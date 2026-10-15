# Time: 2026/10/15
# 笔画预处理 —— 渲染逻辑必须与 Pre_Process/install_dataset_64.py 的 render_drawing 完全一致。
# 区别仅在输入格式：训练时 QuickDraw ndjson 是 [[xs...], [ys...]]，本模块接收前端的 [[x, y], ...] 点列表。
import numpy as np
import cv2
import torch

from app.config import TARGET_SIZE, SRC_SIZE, LINE_THICKNESS


def simplify(stroke, min_dist=2.0):
    """抽稀：与上一点距离 < min_dist 的点丢弃（后端二次抽稀，前端已做一次）。"""
    if not stroke:
        return stroke
    simplified = [stroke[0]]
    for p in stroke[1:]:
        if np.hypot(p[0] - simplified[-1][0], p[1] - simplified[-1][1]) >= min_dist:
            simplified.append(p)
    return simplified


def render_drawing(strokes, size=TARGET_SIZE):
    """把笔画序列渲染成 size×size 的 uint8 灰度图（黑底白线）。

    strokes: [[x, y], ...] 点列表的列表，坐标范围 0~255（SRC_SIZE）。
    """
    img = np.zeros((size, size), dtype=np.uint8)
    scale = size / SRC_SIZE  # 256 -> size

    for stroke in strokes:
        stroke = simplify(stroke)
        if len(stroke) == 0:
            continue

        pts = np.array(stroke, dtype=np.float32)
        pts = np.round(pts * scale).astype(np.int32)
        pts[:, 0] = np.clip(pts[:, 0], 0, size - 1)
        pts[:, 1] = np.clip(pts[:, 1], 0, size - 1)

        if len(pts) == 1:
            cv2.circle(img, tuple(pts[0]), LINE_THICKNESS, 255, -1, lineType=cv2.LINE_AA)
        else:
            cv2.polylines(img, [pts], False, 255, LINE_THICKNESS, lineType=cv2.LINE_AA)

    return img


def to_tensor(img, device):
    """uint8 灰度图 -> (1,1,H,W) float 张量，/255 归一化（与训练时 QuickDrawDataset 一致）。"""
    tensor = torch.from_numpy(img).float().div_(255.0).unsqueeze(0).unsqueeze(0)
    return tensor.to(device)
