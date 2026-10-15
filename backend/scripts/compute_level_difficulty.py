# Time: 2026/10/15
# 一次性脚本：从 test 集每类抽样，统计每类 recall，映射关卡难度 1~5，
# 输出 backend/app/data/level_difficulty.json。
# 用法：cd backend && python -m scripts.compute_level_difficulty
import json
import sys
from pathlib import Path

import numpy as np
import torch

# 保证能 import app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import BASE_DIR, LEVEL_DIFFICULTY_FILE
from app.ml import inference
from app.ml.model import QuickDrawCNN
from app.utils.init_db import difficulty_from_recall

NPZ_PATH = BASE_DIR.parent / "data" / "quickdraw_100class_64" / "quickdraw_100class_64.npz"
MODEL_PATH = BASE_DIR.parent / "model" / "best_model_64.pt"
SAMPLES_PER_CLASS = 200
BATCH_SIZE = 256


def main():
    with np.load(NPZ_PATH) as data:
        X_test, y_test = data["X_test"], data["y_test"]

    ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    class_names = list(ckpt["class_names"])
    model = QuickDrawCNN(len(class_names))
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    rng = np.random.default_rng(42)
    recalls = {}
    for cls_idx in range(len(class_names)):
        idx = np.where(y_test == cls_idx)[0]
        idx = rng.choice(idx, size=min(SAMPLES_PER_CLASS, len(idx)), replace=False)
        correct = 0
        for start in range(0, len(idx), BATCH_SIZE):
            batch = idx[start:start + BATCH_SIZE]
            x = torch.from_numpy(X_test[batch]).float().div_(255.0).unsqueeze(1)
            with torch.no_grad():
                pred = model(x).argmax(1).numpy()
            correct += int((pred == y_test[batch]).sum())
        recalls[class_names[cls_idx]] = correct / len(idx)

    result = {
        cls: {"recall": round(r, 4), "difficulty": difficulty_from_recall(r)}
        for cls, r in sorted(recalls.items(), key=lambda kv: kv[1], reverse=True)
    }

    LEVEL_DIFFICULTY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LEVEL_DIFFICULTY_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"已写入 {LEVEL_DIFFICULTY_FILE}")
    dist = {}
    for info in result.values():
        dist[info["difficulty"]] = dist.get(info["difficulty"], 0) + 1
    print("难度分布:", dict(sorted(dist.items())))


if __name__ == "__main__":
    main()
