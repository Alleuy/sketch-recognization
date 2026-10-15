# Time: 2026/10/15
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.ml import inference
from app.models import Level, Progress
from app.schemas import SubmitRequest, SubmitResponse, LevelItem, LevelListResponse

router = APIRouter(tags=["levels"])


@router.get("/levels", response_model=LevelListResponse)
def list_levels(db: Session = Depends(get_db)):
    """关卡列表（按 id 升序，即难度从易到难）。"""
    levels = db.query(Level).order_by(Level.id).all()
    return {
        "levels": [
            LevelItem(
                id=l.id, class_name=l.class_name,
                display_name=l.display_name or l.class_name,
                difficulty=l.difficulty, pass_threshold=l.pass_threshold,
            ).model_dump()
            for l in levels
        ]
    }


@router.get("/levels/{level_id}", response_model=LevelItem)
def get_level(level_id: int, db: Session = Depends(get_db)):
    level = db.query(Level).get(level_id)
    if level is None:
        raise HTTPException(status_code=404, detail="关卡不存在")
    return LevelItem(
        id=level.id, class_name=level.class_name,
        display_name=level.display_name or level.class_name,
        difficulty=level.difficulty, pass_threshold=level.pass_threshold,
    )


@router.post("/levels/{level_id}/submit", response_model=SubmitResponse)
def submit_level(
    level_id: int,
    req: SubmitRequest,
    x_user_id: str = Header(default="default"),
    db: Session = Depends(get_db),
):
    """提交当前关卡笔画，判定是否通过并更新进度。"""
    level = db.query(Level).get(level_id)
    if level is None:
        raise HTTPException(status_code=404, detail="关卡不存在")
    if not inference.is_loaded():
        raise HTTPException(status_code=503, detail="模型未加载")

    top = inference.predict_topk(req.strokes, k=5)
    top3 = [
        {"class_name": c, "display_name": d, "confidence": f}
        for c, d, f in top[:3]
    ]
    top1_class, _, top1_conf = top[0]

    # 平衡模式判定：top1 命中目标类别且置信度达标
    passed = (top1_class == level.class_name
              and top1_conf >= (level.pass_threshold or 0.5))

    # 目标类别的置信度（可能不在 top5 内）
    target_conf = next(
        (f for c, _, f in top if c == level.class_name), 0.0)

    # 更新进度
    progress = db.query(Progress).filter_by(
        user_id=x_user_id, level_id=level_id).first()
    if progress is None:
        progress = Progress(user_id=x_user_id, level_id=level_id,
                            passed=False, attempts=0, best_confidence=0.0)
        db.add(progress)
    progress.attempts += 1
    if passed:
        progress.passed = True
    progress.best_confidence = max(progress.best_confidence or 0.0, target_conf)
    db.commit()

    # 下一关
    next_level = db.query(Level).filter(Level.id == level_id + 1).first()

    return SubmitResponse(
        passed=passed,
        target_class=level.class_name,
        display_name=level.display_name or level.class_name,
        top3=top3,
        attempts=progress.attempts,
        best_confidence=progress.best_confidence,
        next_level_id=next_level.id if (passed and next_level) else None,
    )
