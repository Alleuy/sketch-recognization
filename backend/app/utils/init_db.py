# Time: 2026/10/15
# 建表 + 关卡播种。
import json
import logging

from sqlalchemy.orm import Session

from app.config import PASS_THRESHOLD, CLASS_NAMES_ZH_FILE, LEVEL_DIFFICULTY_FILE, BASE_DIR
from app.database import Base, engine
from app.models import Level

logger = logging.getLogger("uvicorn")

_CLASS_NAMES_JSON = BASE_DIR.parent / "data" / "quickdraw_100class_64" / "class_names.json"

DEFAULT_DIFFICULTY = 3


def difficulty_from_recall(recall: float) -> int:
    """recall 越高难度越低。"""
    if recall >= 0.95:
        return 1
    if recall >= 0.90:
        return 2
    if recall >= 0.85:
        return 3
    if recall >= 0.75:
        return 4
    return 5


def seed_levels(db: Session) -> int:
    """若 levels 表为空则播种 100 关，按难度升序（简单在前）。返回播种数量。"""
    if db.query(Level).count() > 0:
        return 0

    with open(_CLASS_NAMES_JSON, encoding="utf-8") as f:
        class_names = json.load(f)

    display_names = {}
    if CLASS_NAMES_ZH_FILE.exists():
        with open(CLASS_NAMES_ZH_FILE, encoding="utf-8") as f:
            display_names = json.load(f)

    difficulty_map = {}
    if LEVEL_DIFFICULTY_FILE.exists():
        with open(LEVEL_DIFFICULTY_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        difficulty_map = {
            cls: (info["difficulty"] if isinstance(info, dict) else int(info))
            for cls, info in raw.items()
        }

    # 按难度升序、同难度按类别名稳定排序
    ordered = sorted(
        class_names,
        key=lambda c: (difficulty_map.get(c, DEFAULT_DIFFICULTY), c),
    )

    for idx, cls in enumerate(ordered, start=1):
        db.add(Level(
            id=idx,
            class_name=cls,
            display_name=display_names.get(cls, cls),
            difficulty=difficulty_map.get(cls, DEFAULT_DIFFICULTY),
            pass_threshold=PASS_THRESHOLD,
        ))
    db.commit()
    logger.info("已播种 %d 个关卡", len(ordered))
    return len(ordered)


def init_db():
    """建表 + 播种（应用启动时调用）。"""
    Base.metadata.create_all(bind=engine)
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        seed_levels(db)
    finally:
        db.close()
