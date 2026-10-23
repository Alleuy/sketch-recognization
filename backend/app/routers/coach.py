# Time: 2026/10/22
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.ml import coach, inference
from app.models import Level
from app.schemas import PredictRequest

router = APIRouter(tags=["coach"])


class CoachRequest(PredictRequest):
    level_id: int = Field(..., ge=1)


@router.post("/coach")
def ask_coach(req: CoachRequest, db: Session = Depends(get_db)):
    """绘画导师：几何诊断 + 反事实探针，返回结构化建议。"""
    level = db.get(Level, req.level_id)
    if level is None:
        raise HTTPException(status_code=404, detail="关卡不存在")
    if not inference.is_loaded():
        raise HTTPException(status_code=503, detail="模型未加载")
    try:
        return coach.diagnose(
            req.strokes, level.class_name,
            level.display_name or level.class_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导师分析失败: {e}")
