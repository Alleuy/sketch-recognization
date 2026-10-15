# Time: 2026/10/15
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Level(Base):
    """关卡定义：100 关，每关对应一个类别。"""
    __tablename__ = "levels"

    id = Column(Integer, primary_key=True)  # 1~100
    class_name = Column(String(64), nullable=False, unique=True)
    display_name = Column(String(64))       # 中文显示名
    difficulty = Column(Integer, default=3)  # 1~5，越小越简单
    pass_threshold = Column(Float, default=0.5)


class Progress(Base):
    """用户闯关进度（匿名 UUID 用户）。"""
    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("user_id", "level_id", name="uq_user_level"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), default="default", index=True)
    level_id = Column(Integer, ForeignKey("levels.id"), index=True)
    passed = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    best_confidence = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
