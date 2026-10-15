# Time: 2026/10/15
# 模型推理测试：加载真实模型，用 test 集抽样验证准确率下界与 topk 输出格式。
from pathlib import Path

import numpy as np
import pytest
import torch

from app.config import BASE_DIR, CLASS_NAMES_ZH_FILE, MODEL_PATH

MODEL_EXISTS = Path(MODEL_PATH).exists()
NPZ_PATH = BASE_DIR.parent / "data" / "quickdraw_100class_64" / "quickdraw_100class_64.npz"

pytestmark = pytest.mark.skipif(
    not MODEL_EXISTS or not NPZ_PATH.exists(),
    reason="模型权重或数据集不存在，跳过推理测试",
)

SAMPLES = 500


@pytest.fixture(scope="module")
def loaded():
    from app.ml import inference
    inference.load_model()
    # 注入中文映射，同时验证 display_name 通路
    import json
    if CLASS_NAMES_ZH_FILE.exists():
        with open(CLASS_NAMES_ZH_FILE, encoding="utf-8") as f:
            inference.set_display_names(json.load(f))
    return inference


class TestModelAccuracy:
    def test_testset_accuracy(self, loaded):
        with np.load(NPZ_PATH) as data:
            X_test, y_test = data["X_test"], data["y_test"]
        rng = np.random.default_rng(42)
        idx = rng.choice(len(y_test), size=SAMPLES, replace=False)
        correct = 0
        for start in range(0, SAMPLES, 256):
            b = idx[start:start + 256]
            x = torch.from_numpy(X_test[b]).float().div_(255.0).unsqueeze(1)
            with torch.no_grad():
                pred = loaded._model(x).argmax(1).numpy()
            correct += int((pred == y_test[b]).sum())
        acc = correct / SAMPLES
        assert acc >= 0.80, f"测试集抽样准确率过低: {acc:.3f}"


class TestPredictTopk:
    def test_returns_k_sorted(self, loaded):
        strokes = [
            [[128, 30], [160, 90], [128, 150], [96, 90], [128, 30]],  # 近似菱形
            [[100, 100], [156, 100], [100, 140], [156, 140]],
        ]
        results = loaded.predict_topk(strokes, k=5)
        assert len(results) == 5
        confs = [r[2] for r in results]
        assert confs == sorted(confs, reverse=True)
        for class_name, display, conf in results:
            assert isinstance(class_name, str) and class_name
            assert isinstance(display, str) and display
            assert 0.0 <= conf <= 1.0

    def test_display_name_is_chinese_when_mapped(self, loaded):
        import json
        with open(CLASS_NAMES_ZH_FILE, encoding="utf-8") as f:
            zh = json.load(f)
        strokes = [[[50, 50], [200, 50], [200, 200], [50, 200], [50, 50]]]
        for class_name, display, _ in loaded.predict_topk(strokes, k=5):
            if class_name in zh:
                assert display == zh[class_name]
