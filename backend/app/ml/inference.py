# Time: 2026/10/15
# 模型加载与推理（全局单例 + 线程锁）。
import threading

import torch

from app.config import MODEL_PATH
from app.ml.model import QuickDrawCNN
from app.ml.preprocess import render_drawing, to_tensor

model_lock = threading.Lock()
_model = None
_class_names = None
_display_names = None   # class_name -> 中文名
_device = None


def set_display_names(mapping: dict):
    """注入中文显示名映射（由 main.py 启动时从 json 加载后调用）。"""
    global _display_names
    _display_names = mapping or {}


def load_model(model_path: str = None):
    """加载模型权重并预热。应在应用启动时调用一次。"""
    global _model, _class_names, _device

    path = model_path or MODEL_PATH
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    ckpt = torch.load(path, map_location=_device, weights_only=False)
    _class_names = list(ckpt["class_names"])

    _model = QuickDrawCNN(len(_class_names)).to(_device)
    _model.load_state_dict(ckpt["model_state"])
    _model.eval()

    # 预热：避免首次请求慢
    dummy = torch.zeros(1, 1, 64, 64).to(_device)
    with torch.no_grad():
        _model(dummy)

    return _model


def is_loaded() -> bool:
    return _model is not None


def predict_topk(strokes, k=5):
    """渲染笔画 -> 推理 -> 返回 [(class_name, display_name, confidence), ...] 前 k 项。"""
    if _model is None:
        raise RuntimeError("模型尚未加载，请先调用 load_model()")

    img = render_drawing(strokes)
    tensor = to_tensor(img, _device)

    with model_lock:
        with torch.no_grad():
            logits = _model(tensor)
            probs = torch.softmax(logits, dim=1)[0]

    values, indices = torch.topk(probs, k)
    results = []
    for conf, idx in zip(values.tolist(), indices.tolist()):
        class_name = _class_names[idx]
        display = class_name
        if _display_names is not None:
            display = _display_names.get(class_name, class_name)
        results.append((class_name, display, round(float(conf), 4)))
    return results
