"""RBAC y validación de usuario autenticado para PixelForge Studio."""

from typing import Any, Dict, Iterable, List, Optional, Union

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.service import decode_token


security = HTTPBearer(auto_error=False)


ROLE_HIERARCHY = {
    "admin_juego": {"admin_juego", "moderador", "jugador"},
    "moderador": {"moderador", "jugador"},
    "jugador": {"jugador"},

    # Compatibilidad con roles del parcial anterior.
    "ADMIN": {"ADMIN", "MODERADOR", "JUGADOR", "admin_juego", "moderador", "jugador"},
    "MODERADOR": {"MODERADOR", "JUGADOR", "moderador", "jugador"},
    "JUGADOR": {"JUGADOR", "jugador"},
}


def normalize_role(role: Optional[str]) -> str:
    """Convierte roles antiguos a roles del examen final."""
    if not role:
        return ""

    mapping = {
        "ADMIN": "admin_juego",
        "MODERADOR": "moderador",
        "JUGADOR": "jugador",
    }

    return mapping.get(role, role)


def normalize_allowed_roles(roles: Union[str, Iterable[str]]) -> List[str]:
    """Normaliza entrada de roles permitidos."""
    if isinstance(roles, str):
        roles = [roles]

    return [normalize_role(role) for role in roles]


def extract_token_from_authorization(authorization: Optional[str]) -> str:
    """Extrae el JWT desde el header Authorization."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido.",
        )

    clean = authorization.replace("Bearer ", "").strip()

    if not clean:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido.",
        )

    return clean


def build_current_user_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Construye un usuario actual desde el payload JWT."""
    role = normalize_role(payload.get("role"))
    user_id = payload.get("sub") or payload.get("player_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin identificador de usuario.",
        )

    return {
        "id": int(user_id),
        "sub": str(user_id),
        "role": role,
        "raw_role": payload.get("role"),
        "mfa_verified": bool(payload.get("mfa_verified", True)),
        "token_type": payload.get("token_type", "access"),
        "payload": payload,
    }


def decode_authorization_header(authorization: Optional[str]) -> Dict[str, Any]:
    """Decodifica el JWT desde Authorization y retorna current_user."""
    token = extract_token_from_authorization(authorization)

    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
        )

    return build_current_user_from_payload(payload)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """Dependencia moderna para validar JWT con HTTPBearer."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido.",
        )

    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
        )

    return build_current_user_from_payload(payload)


def role_has_permission(current_role: Optional[str], allowed_roles: Union[str, Iterable[str]]) -> bool:
    """Evalúa si el rol actual tiene permiso según jerarquía."""
    normalized_current = normalize_role(current_role)
    normalized_allowed = set(normalize_allowed_roles(allowed_roles))

    inherited_roles = ROLE_HIERARCHY.get(normalized_current, {normalized_current})

    return bool(inherited_roles.intersection(normalized_allowed))


def verify_role(
    payload_or_allowed_roles: Union[Dict[str, Any], str, Iterable[str]],
    allowed_roles: Optional[Union[str, Iterable[str]]] = None,
):
    """
    Verifica permisos por rol.

    Compatible con dos usos:

    1. Forma vieja del parcial anterior:
       payload: Dict = Depends(verify_role("MODERADOR"))

    2. Forma directa:
       verify_role(current_user, ["admin_juego", "moderador"])
    """

    # Forma vieja / dependencia FastAPI:
    # Depends(verify_role("MODERADOR"))
    if allowed_roles is None:
        required_roles = payload_or_allowed_roles

        async def dependency(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
            current_user = decode_authorization_header(authorization)

            if not role_has_permission(current_user.get("role"), required_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permiso insuficiente.",
                )

            return current_user

        return dependency

    # Forma directa:
    # verify_role(current_user, ["moderador"])
    current_user = payload_or_allowed_roles

    if not isinstance(current_user, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario autenticado inválido.",
        )

    if not role_has_permission(current_user.get("role"), allowed_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permiso insuficiente.",
        )

    return True


def require_role(allowed_roles: Union[str, Iterable[str]]):
    """
    Dependencia moderna para proteger endpoints por rol.

    Uso:
        current_user: dict = Depends(require_role(["admin_juego"]))
    """

    async def dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        verify_role(current_user, allowed_roles)
        return current_user

    return dependency


def require_mfa_verified(current_user: Dict[str, Any]) -> None:
    """Bloquea tokens parciales que todavía no completaron MFA."""
    if current_user.get("token_type") == "partial" or not current_user.get("mfa_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debe completar la verificación MFA.",
        )


def require_self_or_role(
    target_user_id: int,
    current_user: Dict[str, Any],
    allowed_roles: Union[str, Iterable[str]] = ("admin_juego", "moderador"),
) -> bool:
    """
    Previene IDOR.

    Permite acceso si:
    1. El usuario consulta sus propios datos.
    2. El usuario tiene rol administrativo permitido.
    """

    current_id = int(current_user.get("id"))

    if current_id == int(target_user_id):
        return True

    if role_has_permission(current_user.get("role"), allowed_roles):
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tiene permiso para consultar este recurso.",
    )


def require_authorization_header(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """
    Compatibilidad con routers que todavía reciben Authorization manualmente.
    """
    return decode_authorization_header(authorization)