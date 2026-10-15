# Time: 2026/10/15
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL

# SQLite 需要 check_same_thread=False（FastAPI 多线程访问）
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI 依赖：请求级 Session。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
