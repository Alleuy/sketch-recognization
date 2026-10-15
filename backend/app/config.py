# Time: 2026/10/15
import os
from pathlib import Path

# backend/ 目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 模型权重：默认项目根目录下的 model/best_model_64.pt
DEFAULT_MODEL_PATH = BASE_DIR.parent / "model" / "best_model_64.pt"

MODEL_PATH = os.environ.get("MODEL_PATH", str(DEFAULT_MODEL_PATH))

# 数据库：默认 backend/quickdraw.db
DATABASE_URL = os.environ.get(
    "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'quickdraw.db').as_posix()}"
)

# 通关判定默认阈值（平衡模式），可被每关 pass_threshold 覆盖
PASS_THRESHOLD = float(os.environ.get("PASS_THRESHOLD", 0.5))

# 输入限制
MAX_STROKES = 200          # 最大笔画数
MAX_POINTS_PER_STROKE = 512  # 每笔画最大点数
MAX_TOTAL_POINTS = 20000   # 总点数上限

# 预处理常量（必须与 Pre_Process/install_dataset_64.py 保持一致）
TARGET_SIZE = 64
SRC_SIZE = 256
LINE_THICKNESS = 2

# 数据文件
APP_DATA_DIR = BASE_DIR / "app" / "data"
CLASS_NAMES_ZH_FILE = APP_DATA_DIR / "class_names_zh.json"
LEVEL_DIFFICULTY_FILE = APP_DATA_DIR / "level_difficulty.json"
