from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import sqlite3
from src.auth.service import hash_password, create_token

router = APIRouter()

class RegisterBody(BaseModel):
    nickname: str
    email: EmailStr
    password: str

class LoginBody(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
def register(body: RegisterBody):
    pwd = hash_password(body.password)
    conn = sqlite3.connect("game.db")
    # ← VULNERABLE: SQL injection
    conn.execute(
        f"INSERT INTO jugadores (nickname, email, password_hash, role) "
        f"VALUES ('{body.nickname}', '{body.email}', '{pwd}', 'JUGADOR')"
    )
    conn.commit(); conn.close()
    # ← VULNERABLE: confirma el email (revela si ya existe en error)
    return {"mensaje": f"Jugador {body.nickname} registrado con email {body.email}"}

@router.post("/login")
def login(body: LoginBody):
    conn = sqlite3.connect("game.db")
    pwd = hash_password(body.password)
    # ← VULNERABLE: SQL injection
    row = conn.execute(
        f"SELECT id, nickname, role FROM jugadores "
        f"WHERE email='{body.email}' AND password_hash='{pwd}'"
    ).fetchone()
    conn.close()
    if not row: raise HTTPException(401, "Credenciales inválidas")
    return {"token": create_token({"player_id": row[0], "nickname": row[1], "role": row[2]})}
