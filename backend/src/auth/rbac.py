"""Control de acceso basado en roles para PixelForge Studio."""

from typing import Callable, Dict, List

from fastapi import Header, HTTPException, status

from src.auth.service import decode_token


ROLE_HIERARCHY = {
    "ADMIN": ["ADMIN", "MODERADOR", "JUGADOR"],
    "MODERADOR": ["MODERADOR", "JUGADOR"],
    "JUGADOR": ["JUGADOR"],
}


def normalize_role(role: str) -> str:
    """
    Normaliza roles para evitar errores por mayúsculas/minúsculas.
    """
    return role.strip().upper() if role else ""


def get_current_user(authorization: str = Header(None)) -> Dict:
    """
    Valida que exista un JWT, que esté firmado correctamente,
    que no esté expirado y que no esté en blacklist.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token requerido."
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de token inválido."
        )

    try:
        payload = decode_token(authorization)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado."
        )

    if not payload.get("sub") and not payload.get("player_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin sujeto válido."
        )

    return payload


def verify_role(required_role: str) -> Callable:
    """
    Dependency para FastAPI.

    Uso:
    Depends(verify_role("ADMIN"))
    Depends(verify_role("MODERADOR"))
    Depends(verify_role("JUGADOR"))
    """
    required = normalize_role(required_role)

    def dependency(authorization: str = Header(None)) -> Dict:
        payload = get_current_user(authorization)
        user_role = normalize_role(payload.get("role", ""))

        allowed_roles: List[str] = ROLE_HIERARCHY.get(user_role, [])

        if required not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para realizar esta acción."
            )

        return payload

    return dependency


def require_self_or_role(player_id: int, payload: Dict, required_role: str = "ADMIN") -> None:
    """
    Permite acceso si el usuario consulta su propio recurso
    o si tiene un rol administrativo.
    Esto mitiga IDOR en rutas como /jugador/{player_id}/historial.
    """
    token_player_id = str(payload.get("player_id") or payload.get("sub"))
    user_role = normalize_role(payload.get("role", ""))

    if str(player_id) == token_player_id:
        return

    allowed_roles = ROLE_HIERARCHY.get(user_role, [])

    if normalize_role(required_role) in allowed_roles:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permiso para acceder a este recurso."
    )