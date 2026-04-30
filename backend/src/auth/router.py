"""Rutas de autenticación seguras para PixelForge Studio."""

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from src.auth.service import (
    create_token,
    hash_password,
    validate_password_strength,
    verify_password,
)

router = APIRouter()
logger = logging.getLogger("pixelforge.auth")

DB_PATH = "game.db"
MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15
DUMMY_HASH = (
    "$2b$12$u1qA6VfE6MhbBWNORxREkeY2b1a1c0qNJGgspD3U35D.7l1zI4JpG"
)


class RegisterBody(BaseModel):
    nickname: str = Field(
        ...,
        min_length=3,
        max_length=20,
        pattern=r"^[A-Za-z0-9_]+$"
    )
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_security_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS login_attempts (
            email TEXT PRIMARY KEY,
            failed_count INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ip_address TEXT,
            endpoint TEXT NOT NULL,
            user_ref TEXT,
            result TEXT NOT NULL,
            details TEXT
        )
        """
    )

    conn.commit()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


def audit(
    conn: sqlite3.Connection,
    request: Request,
    endpoint: str,
    result: str,
    user_ref: Optional[str] = None,
    details: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO audit_log (
            timestamp, ip_address, endpoint, user_ref, result, details
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            client_ip(request),
            endpoint,
            user_ref,
            result,
            details[:255],
        ),
    )
    conn.commit()


def get_lock_until(conn: sqlite3.Connection, email: str) -> Optional[datetime]:
    row = conn.execute(
        "SELECT locked_until FROM login_attempts WHERE email = ?",
        (email,),
    ).fetchone()

    if not row or not row["locked_until"]:
        return None

    try:
        return datetime.fromisoformat(row["locked_until"])
    except ValueError:
        return None


def is_temporarily_locked(conn: sqlite3.Connection, email: str) -> bool:
    locked_until = get_lock_until(conn, email)

    if not locked_until:
        return False

    return locked_until > datetime.now(timezone.utc)


def register_failed_login(conn: sqlite3.Connection, email: str) -> None:
    now = datetime.now(timezone.utc)
    row = conn.execute(
        "SELECT failed_count FROM login_attempts WHERE email = ?",
        (email,),
    ).fetchone()

    failed_count = 1 if not row else int(row["failed_count"]) + 1
    locked_until = None

    if failed_count >= MAX_FAILED_ATTEMPTS:
        locked_until = (now + timedelta(minutes=LOCK_MINUTES)).isoformat()

    conn.execute(
        """
        INSERT INTO login_attempts (
            email, failed_count, locked_until, updated_at
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET
            failed_count = excluded.failed_count,
            locked_until = excluded.locked_until,
            updated_at = excluded.updated_at
        """,
        (email, failed_count, locked_until, now.isoformat()),
    )

    conn.commit()


def reset_failed_login(conn: sqlite3.Connection, email: str) -> None:
    conn.execute(
        """
        INSERT INTO login_attempts (
            email, failed_count, locked_until, updated_at
        )
        VALUES (?, 0, NULL, ?)
        ON CONFLICT(email) DO UPDATE SET
            failed_count = 0,
            locked_until = NULL,
            updated_at = excluded.updated_at
        """,
        (email, datetime.now(timezone.utc).isoformat()),
    )

    conn.commit()


@router.post("/register")
def register(body: RegisterBody, request: Request):
    conn = get_conn()
    init_security_tables(conn)

    try:
        validate_password_strength(body.password)

        existing = conn.execute(
            """
            SELECT id
            FROM jugadores
            WHERE email = ? OR nickname = ?
            """,
            (body.email, body.nickname),
        ).fetchone()

        if existing:
            audit(
                conn,
                request,
                "/api/auth/register",
                "rejected",
                body.email,
                "email_or_nickname_already_exists",
            )
            raise HTTPException(
                status_code=400,
                detail="No fue posible completar el registro."
            )

        pwd = hash_password(body.password)

        conn.execute(
            """
            INSERT INTO jugadores (
                nickname, email, password_hash, role
            )
            VALUES (?, ?, ?, ?)
            """,
            (body.nickname, body.email, pwd, "JUGADOR"),
        )

        conn.commit()

        audit(
            conn,
            request,
            "/api/auth/register",
            "success",
            body.email,
            "player_registered",
        )

        return {
            "mensaje": "Registro completado correctamente."
        }

    except HTTPException:
        raise

    except ValueError:
        audit(
            conn,
            request,
            "/api/auth/register",
            "rejected",
            body.email,
            "weak_password",
        )
        raise HTTPException(
            status_code=400,
            detail="No fue posible completar el registro."
        )

    except sqlite3.Error:
        logger.exception("Error controlado durante registro")
        audit(
            conn,
            request,
            "/api/auth/register",
            "error",
            body.email,
            "database_error",
        )
        raise HTTPException(
            status_code=400,
            detail="No fue posible completar el registro."
        )

    finally:
        conn.close()


@router.post("/login")
def login(body: LoginBody, request: Request):
    conn = get_conn()
    init_security_tables(conn)

    try:
        if is_temporarily_locked(conn, body.email):
            audit(
                conn,
                request,
                "/api/auth/login",
                "blocked",
                body.email,
                "temporary_lock",
            )
            raise HTTPException(
                status_code=401,
                detail="Credenciales inválidas."
            )

        row = conn.execute(
            """
            SELECT id, nickname, role, password_hash, estado
            FROM jugadores
            WHERE email = ?
            """,
            (body.email,),
        ).fetchone()

        stored_hash = row["password_hash"] if row else DUMMY_HASH
        password_ok = verify_password(body.password, stored_hash)

        if not row or not password_ok or row["estado"] != "activo":
            register_failed_login(conn, body.email)
            audit(
                conn,
                request,
                "/api/auth/login",
                "failed",
                body.email,
                "invalid_credentials",
            )
            raise HTTPException(
                status_code=401,
                detail="Credenciales inválidas."
            )

        reset_failed_login(conn, body.email)

        token = create_token(
            {
                "player_id": row["id"],
                "nickname": row["nickname"],
                "role": row["role"],
            }
        )

        audit(
            conn,
            request,
            "/api/auth/login",
            "success",
            f"user_{row['id']}",
            "jwt_issued",
        )

        return {
            "token": token,
            "token_type": "bearer"
        }

    finally:
        conn.close()