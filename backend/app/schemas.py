# Time: 2026/10/15
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------- 请求 ----------

class PredictRequest(BaseModel):
    """笔画数据：strokes[笔画][点][x, y]，坐标范围 0~255。"""
    strokes: List[List[List[float]]] = Field(..., min_length=1)

    @field_validator("strokes")
    @classmethod
    def check_strokes(cls, v):
        from app.config import MAX_STROKES, MAX_TOTAL_POINTS, MAX_POINTS_PER_STROKE
        if len(v) > MAX_STROKES:
            raise ValueError(f"笔画数超过上限 {MAX_STROKES}")
        total = 0
        for stroke in v:
            if len(stroke) > MAX_POINTS_PER_STROKE:
                raise ValueError(f"单笔画点数超过上限 {MAX_POINTS_PER_STROKE}")
            total += len(stroke)
        if total > MAX_TOTAL_POINTS:
            raise ValueError(f"总点数超过上限 {MAX_TOTAL_POINTS}")
        return v


class SubmitRequest(PredictRequest):
    """提交关卡判定。用户身份从 X-User-ID header 获取。"""
    pass


# ---------- 响应 ----------

class PredictionItem(BaseModel):
    class_name: str
    display_name: str
    confidence: float


class PredictResponse(BaseModel):
    top5: List[PredictionItem]


class LevelItem(BaseModel):
    id: int
    class_name: str
    display_name: str
    difficulty: int
    pass_threshold: float


class LevelListResponse(BaseModel):
    levels: List[LevelItem]


class SubmitResponse(BaseModel):
    passed: bool
    target_class: str
    display_name: str
    top3: List[PredictionItem]
    attempts: int
    best_confidence: float
    next_level_id: Optional[int] = None


class ProgressItem(BaseModel):
    level_id: int
    passed: bool
    attempts: int
    best_confidence: float


class ProgressResponse(BaseModel):
    user_id: str
    passed_count: int
    total: int
    levels: List[ProgressItem]
