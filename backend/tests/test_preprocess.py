# Time: 2026/10/15
# 预处理一致性测试：点列表格式渲染必须与训练数据渲染（install_dataset_64.py）逐像素一致。
import numpy as np
import cv2

from app.config import TARGET_SIZE, SRC_SIZE, LINE_THICKNESS
from app.ml.preprocess import render_drawing, simplify, to_tensor


# ---- 参考实现：原样复制自 Pre_Process/install_dataset_64.py 的 render_drawing ----
def reference_render(drawing, size=TARGET_SIZE):
    """drawing: QuickDraw ndjson 格式 [[xs...], [ys...]]"""
    img = np.zeros((size, size), dtype=np.uint8)
    scale = size / SRC_SIZE
    for stroke in drawing:
        if not isinstance(stroke, (list, tuple)) or len(stroke) != 2:
            continue
        xs, ys = stroke
        if len(xs) == 0:
            continue
        pts = np.stack([xs, ys], axis=1).astype(np.float32)
        pts = np.round(pts * scale).astype(np.int32)
        pts[:, 0] = np.clip(pts[:, 0], 0, size - 1)
        pts[:, 1] = np.clip(pts[:, 1], 0, size - 1)
        if len(pts) == 1:
            cv2.circle(img, tuple(pts[0]), LINE_THICKNESS, 255, -1, lineType=cv2.LINE_AA)
        else:
            cv2.polylines(img, [pts], False, 255, LINE_THICKNESS, lineType=cv2.LINE_AA)
    return img


# 点距 >= 2 的稀疏笔画（与前端抽稀后的真实输入一致），保证 simplify 不改变点集
SPARSE_STROKES = [
    [[10, 20], [30, 42], [55, 66], [80, 90], [120, 140], [200, 210]],
    [[50, 200], [60, 188], [75, 170], [100, 150]],
    [[130, 30], [150, 30], [170, 35]],
]


def to_ndjson(strokes):
    """点列表 -> QuickDraw [[xs],[ys]] 格式。"""
    return [[[p[0] for p in s], [p[1] for p in s]] for s in strokes]


class TestRenderConsistency:
    def test_pixel_identical_with_training_render(self):
        ours = render_drawing(SPARSE_STROKES)
        ref = reference_render(to_ndjson(SPARSE_STROKES))
        assert np.array_equal(ours, ref)

    def test_single_point_stroke_draws_circle(self):
        img = render_drawing([[[128, 128]]])
        ref = reference_render([[[128], [128]]])
        assert np.array_equal(img, ref)
        assert img[32, 32] > 0  # 128 * 64/256 = 32

    def test_out_of_range_clipped(self):
        img = render_drawing([[[-20, -10], [300, 280], [260, 260]]])
        assert img.shape == (TARGET_SIZE, TARGET_SIZE)
        assert img.any()  # 有像素被画出

    def test_empty_strokes_render_black(self):
        img = render_drawing([])
        assert not img.any()

    def test_output_range(self):
        img = render_drawing(SPARSE_STROKES)
        assert img.dtype == np.uint8
        assert img.max() <= 255


class TestSimplify:
    def test_dense_points_removed(self):
        stroke = [[0, 0], [0.5, 0.5], [1, 1], [1.2, 1.2], [5, 5]]
        out = simplify(stroke, min_dist=2.0)
        assert out == [[0, 0], [5, 5]]

    def test_sparse_untouched(self):
        assert simplify(SPARSE_STROKES[0]) == SPARSE_STROKES[0]

    def test_empty(self):
        assert simplify([]) == []


class TestToTensor:
    def test_shape_and_range(self):
        import torch
        img = render_drawing(SPARSE_STROKES)
        t = to_tensor(img, torch.device("cpu"))
        assert t.shape == (1, 1, TARGET_SIZE, TARGET_SIZE)
        assert t.dtype == torch.float32
        assert 0.0 <= float(t.min()) <= float(t.max()) <= 1.0
