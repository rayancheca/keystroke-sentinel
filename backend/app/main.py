from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.models.database import init_db
from app.api.enrollment import router as enrollment_router
from app.api.websocket import router as ws_router
from app.core.config import settings
from app.core.logging import configure_logging, logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await init_db()
    logger.info("Keystroke Sentinel API started")
    yield
    logger.info("Keystroke Sentinel API shutting down")


app = FastAPI(
    title="Keystroke Sentinel API",
    description="Real-time behavioral biometric authentication via keystroke dynamics",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(enrollment_router)
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "keystroke-sentinel"}
