from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.auth.router import router as auth_router
from src.game.router import router as game_router
from src.leaderboard.router import router as lb_router
from src.admin.router import router as admin_router

app = FastAPI(title="PixelForge Studio API", version="1.0.0")

app.add_middleware(CORSMiddleware,
    allow_origins=["https://pixelforge-grupoN.lab.umng.edu.co"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(game_router, prefix="/api/game", tags=["game"])
app.include_router(lb_router, prefix="/api", tags=["leaderboard"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])

@app.get("/health")
def health(): return {"status": "ok"}
