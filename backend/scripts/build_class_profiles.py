# Time: 2026/10/22
# 一次性脚本：统计每个类别 test 集的几何画像（覆盖率/墨量/重心偏移/宽高比），
# 供绘画导师对比"用户画得比标准样本小多少"。输出 backend/app/data/class_profiles.json。
# 用法：cd backend && python -m scripts.build_class_profiles
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import APP_DATA_DIR, BASE_DIR
from app.ml.coach import image_stats

DATA_DIR = BASE_DIR.parent / "data" / "quickdraw_100class_64"
NPZ_PATH = DATA_DIR / "quickdraw_100class_64.npz"
NAMES_PATH = DATA_DIR / "class_names.json"
OUT_PATH = APP_DATA_DIR / "class_profiles.json"

SAMPLES_PER_CLASS = 200


def main():
    with np.load(NPZ_PATH) as data:
        X_test, y_test = data["X_test"], data["y_test"]

    with open(NAMES_PATH, encoding="utf-8") as f:
        class_names = json.load(f)
    if isinstance(class_names, dict):
        class_names = [class_names[str(i)] for i in range(len(class_names))]

    rng = np.random.default_rng(42)
    result = {}
    for idx, name in enumerate(class_names):
        rows = np.where(y_test == idx)[0]
        if len(rows) == 0:
            continue
        rows = rng.choice(rows, size=min(SAMPLES_PER_CLASS, len(rows)), replace=False)

        stats = [image_stats(X_test[i]) for i in rows]
        coverage = np.array([s["coverage"] for s in stats])
        offset = np.array([s["offset"] for s in stats])
        ink = np.array([s["ink_ratio"] for s in stats])
        aspect = np.array([s["aspect"] for s in stats])

        result[name] = {
            "samples": len(rows),
            "coverage_p10": round(float(np.percentile(coverage, 10)), 4),
            "coverage_p50": round(float(np.percentile(coverage, 50)), 4),
            "coverage_p90": round(float(np.percentile(coverage, 90)), 4),
            "offset_p50": round(float(np.percentile(offset, 50)), 4),
            "offset_p90": round(float(np.percentile(offset, 90)), 4),
            "ink_ratio_p50": round(float(np.percentile(ink, 50)), 4),
            "aspect_p50": round(float(np.percentile(aspect, 50)), 4),
        }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"已写入 {OUT_PATH}，类别数：{len(result)}")
    cov = [v["coverage_p50"] for v in result.values()]
    print(f"覆盖率中位数范围：{min(cov):.2f} ~ {max(cov):.2f}")


if __name__ == "__main__":
    main()
