"""Servicio de autenticacion seguro para PixelForge Studio."""

import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt
from passlib.context import CryptContext


JWT_SECRET = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET_KEY no esta configurado. Defina esta variable en el entorno o en el archivo .env."
    )


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

TOKEN_BLACKLIST = set()

PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"
)


def validate_password_strength(password: str) -> None:
    """
    Valida la complejidad minima de la contrasena en backend.
    """
    if not PASSWORD_REGEX.match(password):
        raise ValueError(
            "La contrasena no cumple los requisitos minimos de seguridad."
        )


def hash_password(password: str) -> str:
    """
    Genera hash seguro con bcrypt.
    """
    validate_password_strength(password)
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifica una contrasena usando bcrypt.
    """
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_token(data: Dict[str, Any]) -> str:
    """
    Crea un JWT seguro con sub, role, exp, iat y jti.
    """
    now = datetime.now(timezone.utc)
    expire_minutes = min(JWT_EXPIRE_MINUTES, 60)
    expire = now + timedelta(minutes=expire_minutes)

    payload = data.copy()

    if "player_id" in payload:
        payload["sub"] = str(payload["player_id"])

    payload.update({
        "iat": int(now.timestamp()),
        "exp": expire,
        "jti": str(uuid.uuid4())
    })

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodifica y valida un JWT.
    """
    try:
        clean_token = token.replace("Bearer ", "").strip()
        payload = jwt.decode(
            clean_token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

        jti = payload.get("jti")
        if jti in TOKEN_BLACKLIST:
            raise ValueError("Token invalidado")

        return payload

    except JWTError:
        raise ValueError("Token invalido o expirado")


def blacklist_token(token: str) -> None:
    """
    Invalida un JWT agregando su jti a la blacklist.
    """
    payload = decode_token(token)
    jti = payload.get("jti")

    if jti:
        TOKEN_BLACKLIST.add(jti)
