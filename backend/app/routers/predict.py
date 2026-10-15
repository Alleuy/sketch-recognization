# Time: 2026/10/15
from fastapi import APIRouter, HTTPException

from app.ml import inference
from app.schemas import PredictRequest, PredictResponse

router = APIRouter(tags=["predict"])


@router.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    """通用预测：返回 top5 类别与置信度。"""
    if not inference.is_loaded():
        raise HTTPException(status_code=503, detail="模型未加载")
    try:
        top = inference.predict_topk(req.strokes, k=5)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推理失败: {e}")
    return {
        "top5": [
            {"class_name": c, "display_name": d, "confidence": f}
            for c, d, f in top
        ]
    }
