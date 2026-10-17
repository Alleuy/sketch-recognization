# Time: 2026/10/17
# 一次性脚本：为每类生成一张"参考提示图"，供前端连续 5 次未通关后展示。
# 选图策略（三层质量保证）：
#   1. 数据源：Quick Draw 官方数据，采集时已过滤 recognized=True（真人画且被其他玩家猜中过）
#   2. 模型背书：只在"模型正确分类且置信度最高"的 test 样本里挑图，保证参考图一定能被判定系统识别
#   3. 人工抽查：自动生成 hint_gallery.html 百图总览页，肉眼快速复核，坏图可用 --rank 换
# 输出：
#   backend/app/static/hints/{class_name}.png   前端 <img> 直接引用
#   backend/app/static/hints/manifest.json      每张图的选样元数据（置信度、样本下标）
#   backend/scripts/hint_gallery.html           人工抽查总览页
# 用法：cd backend && python -m scripts.generate_hint_images [--rank N]
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import BASE_DIR
from app.ml.model import QuickDrawCNN

NPZ_PATH = BASE_DIR.parent / "data" / "quickdraw_100class_64" / "quickdraw_100class_64.npz"
MODEL_PATH = BASE_DIR.parent / "model" / "best_model_64.pt"
HINT_DIR = BASE_DIR / "static" / "hints"
GALLERY_FILE = Path(__file__).resolve().parent / "hint_gallery.html"
BATCH_SIZE = 512
# 低于该置信度的"最优正确样本"需人工重点抽查
REVIEW_THRESHOLD = 0.90


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rank", type=int, default=1,
                        help="每类取置信度第 N 高的正确样本（默认 1；发现坏图可换 2、3...）")
    args = parser.parse_args()

    with np.load(NPZ_PATH) as data:
        X_test, y_test = data["X_test"], data["y_test"]

    ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    class_names = list(ckpt["class_names"])
    model = QuickDrawCNN(len(class_names))
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    # 全量 test 集批量推理，拿到每张样本的 top1 置信度
    n = len(X_test)
    probs = np.empty(n, dtype=np.float32)
    preds = np.empty(n, dtype=np.int64)
    with torch.no_grad():
        for start in range(0, n, BATCH_SIZE):
            x = torch.from_numpy(X_test[start:start + BATCH_SIZE]).float().div_(255.0).unsqueeze(1)
            out = torch.softmax(model(x), dim=1)
            conf, pred = out.max(1)
            probs[start:start + BATCH_SIZE] = conf.numpy()
            preds[start:start + BATCH_SIZE] = pred.numpy()

    HINT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}
    need_review = []
    for cls_idx, cls in enumerate(class_names):
        idx = np.where(y_test == cls_idx)[0]
        correct = idx[preds[idx] == cls_idx]
        if len(correct) == 0:  # 理论上不会发生（最低 recall 也有 0.75）
            fallback = idx[np.argmax(probs[idx])]
            pick = int(fallback)
            note = "无正确样本，退回最高置信度样本（需人工复核）"
            need_review.append(cls)
        else:
            order = np.argsort(-probs[correct])
            pick_idx = min(args.rank - 1, len(order) - 1)
            pick = int(correct[order[pick_idx]])
            note = ""
            if probs[pick] < REVIEW_THRESHOLD:
                need_review.append(cls)

        img = Image.fromarray(X_test[pick].astype(np.uint8), mode="L")
        img = img.resize((256, 256), Image.LANCZOS)
        img.save(HINT_DIR / f"{cls}.png")
        manifest[cls] = {
            "file": f"{cls}.png",
            "confidence": round(float(probs[pick]), 4),
            "sample_idx": pick,
        }
        if note:
            manifest[cls]["note"] = note

    with open(HINT_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 生成人工抽查总览页
    cells = "".join(
        f'<div style="text-align:center;font-size:12px;">'
        f'<img src="../app/static/hints/{m["file"]}" style="width:96px;height:96px;display:block;">'
        f'{cls}<br>{m["confidence"]:.3f}</div>'
        for cls, m in manifest.items()
    )
    GALLERY_FILE.write_text(
        "<html><body style='background:#222;color:#eee;font-family:sans-serif;'>"
        f"<h2>参考图总览（rank={args.rank}）— 共 {len(manifest)} 张，肉眼复核用</h2>"
        f"<div style='display:grid;grid-template-columns:repeat(10,1fr);gap:8px;'>{cells}</div>"
        "</body></html>",
        encoding="utf-8",
    )

    print(f"已生成 {len(manifest)} 张参考图 -> {HINT_DIR}")
    print(f"抽查总览页 -> {GALLERY_FILE}")
    if need_review:
        print(f"[注意] 以下 {len(need_review)} 类最优样本置信度 < {REVIEW_THRESHOLD}，建议打开总览页重点检查：")
        print("  " + "、".join(need_review))
    else:
        print(f"全部类别最优样本置信度均 >= {REVIEW_THRESHOLD}，质量良好")


if __name__ == "__main__":
    main()
