"""Rutas de autenticación para PixelForge Studio — Examen Final."""

from datetime import datetime, timedelta

from typing import Optional

from asyncpg import UniqueViolationError
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from src.auth.service import create_token, hash_password, verify_password
from src.db import execute, fetchrow, fetchval
from src.security_logger import log_security_event


router = APIRouter(prefix="/auth", tags=["auth"])


MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 10


class RegisterBody(BaseModel):
    nickname: str = Field(
        min_length=3,
        max_length=20,
        pattern=r"^[a-zA-Z0-9_]+$"
    )
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, value: str) -> str:
        has_upper = any(char.isupper() for char in value)
        has_lower = any(char.islower() for char in value)
        has_digit = any(char.isdigit() for char in value)
        has_special = any(not char.isalnum() for char in value)

        if not all([has_upper, has_lower, has_digit, has_special]):
            raise ValueError(
                "La contraseña debe tener mayúscula, minúscula, número y carácter especial."
            )

        return value


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int = 120
    role: str
    user_id: int
    mfa_required: bool = False


def get_client_ip(request: Request) -> str:
    """Obtiene IP del cliente, considerando proxy si existe."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


async def count_recent_failed_attempts(email: str, ip_address: str) -> int:
    """Cuenta fallos recientes por email o IP en ventana de bloqueo."""
    since = datetime.utcnow() - timedelta(minutes=LOCKOUT_MINUTES)

    count = await fetchval(
        """
        SELECT COUNT(*)
        FROM login_attempts
        WHERE success = FALSE
          AND created_at >= $1
          AND (email = $2 OR ip_address = $3)
        """,
        since,
        email.lower(),
        ip_address,
    )

    return int(count or 0)


async def register_login_attempt(
    email: str,
    ip_address: str,
    success: bool,
    reason: Optional[str] = None,
) -> None:
    """Guarda intento de login en PostgreSQL."""
    await execute(
        """
        INSERT INTO login_attempts(email, ip_address, success, reason)
        VALUES($1, $2, $3, $4)
        """,
        email.lower(),
        ip_address,
        success,
        reason,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterBody, request: Request):
    """Registra un jugador usando PostgreSQL y bcrypt."""

    ip_address = get_client_ip(request)

    try:
        password_hash = hash_password(body.password)

        row = await fetchrow(
            """
            INSERT INTO jugadores(nickname, email, password_hash, role, estado, token_balance)
            VALUES($1, $2, $3, $4, $5, $6)
            RETURNING id, nickname, email, role, estado, token_balance, created_at
            """,
            body.nickname,
            body.email.lower(),
            password_hash,
            "jugador",
            "activo",
            0,
        )

        log_security_event(
            event_type="player_registered",
            ip_address=ip_address,
            user_email=body.email.lower(),
            user_id=row["id"],
            role=row["role"],
            success=True,
            reason="registro_exitoso",
        )

        return {
            "message": "Registro exitoso.",
            "player": {
                "id": row["id"],
                "nickname": row["nickname"],
                "email": row["email"],
                "role": row["role"],
                "estado": row["estado"],
                "token_balance": row["token_balance"],
                "created_at": str(row["created_at"]),
            },
        }

    except UniqueViolationError:
        log_security_event(
            event_type="player_register_failed",
            ip_address=ip_address,
            user_email=body.email.lower(),
            success=False,
            reason="nickname_or_email_duplicated",
        )

        # Mensaje genérico para evitar enumeración de usuarios.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fue posible completar el registro.",
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Datos de registro inválidos.",
        )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginBody, request: Request):
    """Login de jugador con bloqueo temporal por intentos fallidos."""

    ip_address = get_client_ip(request)
    email = body.email.lower()

    recent_failures = await count_recent_failed_attempts(email, ip_address)

    if recent_failures >= MAX_LOGIN_ATTEMPTS:
        await register_login_attempt(
            email=email,
            ip_address=ip_address,
            success=False,
            reason="temporary_lockout",
        )

        log_security_event(
            event_type="login_blocked",
            ip_address=ip_address,
            user_email=email,
            success=False,
            reason="too_many_failed_attempts",
            extra={
                "lockout_minutes": LOCKOUT_MINUTES,
                "recent_failures": recent_failures,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos fallidos. Intente más tarde.",
        )

    user = await fetchrow(
        """
        SELECT id, nickname, email, password_hash, role, estado, mfa_enabled
        FROM jugadores
        WHERE email = $1
        """,
        email,
    )

    # Mensaje genérico: no revela si el usuario existe o si falló la contraseña.
    invalid_credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas.",
    )

    if not user:
        await register_login_attempt(
            email=email,
            ip_address=ip_address,
            success=False,
            reason="invalid_credentials",
        )

        log_security_event(
            event_type="login_failed",
            ip_address=ip_address,
            user_email=email,
            success=False,
            reason="invalid_credentials",
        )

        raise invalid_credentials_error

    if user["estado"] != "activo":
        await register_login_attempt(
            email=email,
            ip_address=ip_address,
            success=False,
            reason="inactive_account",
        )

        log_security_event(
            event_type="login_failed",
            ip_address=ip_address,
            user_email=email,
            user_id=user["id"],
            role=user["role"],
            success=False,
            reason="inactive_account",
        )

        raise invalid_credentials_error

    if not verify_password(body.password, user["password_hash"]):
        await register_login_attempt(
            email=email,
            ip_address=ip_address,
            success=False,
            reason="invalid_credentials",
        )

        log_security_event(
            event_type="login_failed",
            ip_address=ip_address,
            user_email=email,
            user_id=user["id"],
            role=user["role"],
            success=False,
            reason="invalid_credentials",
        )

        raise invalid_credentials_error

    await register_login_attempt(
        email=email,
        ip_address=ip_address,
        success=True,
        reason="login_success",
    )

    await execute(
        """
        UPDATE jugadores
        SET last_login = NOW()
        WHERE id = $1
        """,
        user["id"],
    )

    log_security_event(
        event_type="login_success",
        ip_address=ip_address,
        user_email=email,
        user_id=user["id"],
        role=user["role"],
        success=True,
        reason="credentials_valid",
        extra={
            "mfa_enabled": bool(user["mfa_enabled"]),
        },
    )

    # En la siguiente fase, si mfa_enabled=True emitiremos token parcial.
    # Por ahora se mantiene token completo para usuarios sin MFA.
    token = create_token(
        {
            "player_id": user["id"],
            "sub": str(user["id"]),
            "role": user["role"],
            "mfa_verified": not bool(user["mfa_enabled"]),
            "token_type": "access",
        }
    )

    return TokenResponse(
        access_token=token,
        expires_in_minutes=120,
        role=user["role"],
        user_id=user["id"],
        mfa_required=bool(user["mfa_enabled"]),
    )


@router.get("/me")
async def me():
    """Endpoint reservado para completar perfil autenticado en fases posteriores."""
    return {
        "message": "Perfil autenticado pendiente de integración con RBAC final."
    }