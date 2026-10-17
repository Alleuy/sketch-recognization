# Time: 2026/10/15
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, MODEL_PATH, CLASS_NAMES_ZH_FILE
from app.ml import inference
from app.routers import predict, levels, progress
from app.utils.init_db import init_db

logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 建表 + 播种关卡
    init_db()
    # 2. 加载中文显示名
    display_names = {}
    if CLASS_NAMES_ZH_FILE.exists():
        with open(CLASS_NAMES_ZH_FILE, encoding="utf-8") as f:
            display_names = json.load(f)
    inference.set_display_names(display_names)
    # 3. 加载模型并预热
    import os
    if os.path.exists(MODEL_PATH):
        inference.load_model()
        logger.info("模型加载并预热完成: %s", MODEL_PATH)
    else:
        logger.warning("模型文件不存在，/predict 与 /submit 将返回 503: %s", MODEL_PATH)
    yield


app = FastAPI(
    title="QuickDraw 草图识别闯关系统 API",
    version="0.1.0",
    lifespan=lifespan,
)

# MVP：前端为静态页面直接打开，放开 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict.router, prefix="/api")
app.include_router(levels.router, prefix="/api")
app.include_router(progress.router, prefix="/api")

# 关卡参考提示图（generate_hint_images.py 产出）
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/api/health")
def health():
    return {"status": "ok", "model_loaded": inference.is_loaded()}
