# Time: 2026/10/15
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Level, Progress
from app.schemas import ProgressResponse, ProgressItem

router = APIRouter(tags=["progress"])


@router.get("/progress", response_model=ProgressResponse)
def get_progress(x_user_id: str = Header(default="default"),
                 db: Session = Depends(get_db)):
    """获取用户闯关进度。"""
    total = db.query(Level).count()
    rows = db.query(Progress).filter_by(user_id=x_user_id).all()
    return ProgressResponse(
        user_id=x_user_id,
        passed_count=sum(1 for r in rows if r.passed),
        total=total,
        levels=[
            ProgressItem(level_id=r.level_id, passed=r.passed,
                         attempts=r.attempts, best_confidence=r.best_confidence)
            for r in rows
        ],
    )
