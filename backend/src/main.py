"""Aplicación principal FastAPI para PixelForge Studio."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.admin.router import router as admin_router
from src.auth.router import router as auth_router
from src.db import connect_db, disconnect_db, fetchval
from src.game.router import router as game_router
from src.leaderboard.router import router as leaderboard_router
from src.payments.router import router as payments_router
from src.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Inicializa y cierra recursos globales de la aplicación.
    """
    await connect_db()
    yield
    await disconnect_db()


settings = get_settings()

app = FastAPI(
    title="PixelForge Studio API",
    description="Backend seguro para PixelForge Studio — Examen Final Caso B",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "pixelforge-api",
        "version": "2.0.0"
    }


@app.get("/health/db")
async def health_db():
    db_now = await fetchval("SELECT NOW()")
    table_count = await fetchval(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
    )

    return {
        "status": "ok",
        "database": "postgresql",
        "db_time": str(db_now),
        "tables": table_count
    }


app.include_router(auth_router)
app.include_router(game_router)
app.include_router(leaderboard_router)
app.include_router(admin_router)
app.include_router(payments_router)