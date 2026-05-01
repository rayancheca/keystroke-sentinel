from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Float, Integer, DateTime, Text
from datetime import datetime
from app.core.config import settings


engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class UserEnrollment(Base):
    __tablename__ = "user_enrollments"

    user_id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    keystroke_count = Column(Integer, default=0)
    is_trained = Column(Integer, default=0)  # 0=pending, 1=trained
    model_path = Column(String, nullable=True)
    accuracy = Column(Float, nullable=True)
    feature_importance = Column(Text, nullable=True)  # JSON blob


class KeystrokeSession(Base):
    __tablename__ = "keystroke_sessions"

    session_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    anomaly_score = Column(Float, nullable=True)
    is_flagged = Column(Integer, default=0)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
