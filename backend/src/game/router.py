"""Rutas de juego y registro seguro de puntajes."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from src.auth.rbac import require_role
from src.db import execute, fetchrow, fetchval
from src.security_logger import log_security_event


router = APIRouter(prefix="/game", tags=["game"])


MAX_SCORE_ALLOWED = 100000
SCORE_RATE_LIMIT_SECONDS = 60


class StartGameResponse(BaseModel):
    session_token: str
    message: str


class ScoreBody(BaseModel):
    """
    Body permitido para registrar puntaje.

    Importante:
    - No existe player_id en el body.
    - Si el cliente envía player_id, Pydantic lo rechaza por extra='forbid'.
    """

    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=1, le=MAX_SCORE_ALLOWED)
    level_reached: int = Field(ge=1, le=10)
    session_token: Optional[str] = None


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


@router.post("/start", response_model=StartGameResponse)
async def start_game(
    request: Request,
    current_user: dict = Depends(require_role("jugador")),
):
    """
    Crea una sesión de partida para el jugador autenticado.

    El jugador se toma exclusivamente del JWT.
    """

    session_token = uuid4()
    player_id = current_user["id"]
    ip_address = get_client_ip(request)

    await execute(
        """
        INSERT INTO partidas(session_token, jugador_id)
        VALUES($1, $2)
        """,
        session_token,
        player_id,
    )

    log_security_event(
        event_type="game_session_started",
        ip_address=ip_address,
        user_id=player_id,
        role=current_user["role"],
        success=True,
        reason="session_created",
        extra={"session_token_prefix": str(session_token)[:8]},
    )

    return StartGameResponse(
        session_token=str(session_token),
        message="Partida iniciada correctamente.",
    )


@router.post("/score", status_code=status.HTTP_201_CREATED)
async def register_score(
    body: ScoreBody,
    request: Request,
    current_user: dict = Depends(require_role("jugador")),
):
    """
    Registra un puntaje de forma segura.

    Reglas:
    - Requiere JWT con rol jugador.
    - El jugador se toma del token, nunca del body.
    - El score debe estar entre 1 y MAX_SCORE_ALLOWED.
    - Rate limit: máximo 1 puntaje por minuto por jugador.
    - Si llega session_token, se valida ownership y uso único.
    """

    player_id = current_user["id"]
    ip_address = get_client_ip(request)

    recent_scores = await fetchval(
        """
        SELECT COUNT(*)
        FROM puntuaciones
        WHERE jugador_id = $1
          AND created_at >= NOW() - INTERVAL '1 minute'
        """,
        player_id,
    )

    if int(recent_scores or 0) >= 1:
        log_security_event(
            event_type="score_rate_limited",
            ip_address=ip_address,
            user_id=player_id,
            role=current_user["role"],
            success=False,
            reason="score_rate_limit_1_per_minute",
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Solo puede registrar un puntaje por minuto.",
        )

    partida_id = None

    if body.session_token:
        try:
            parsed_session = UUID(body.session_token)
        except ValueError:
            log_security_event(
                event_type="score_rejected",
                ip_address=ip_address,
                user_id=player_id,
                role=current_user["role"],
                success=False,
                reason="invalid_session_token_format",
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session token inválido.",
            )

        partida = await fetchrow(
            """
            SELECT id, jugador_id, usado
            FROM partidas
            WHERE session_token = $1
            """,
            parsed_session,
        )

        if not partida:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Partida no encontrada.",
            )

        if int(partida["jugador_id"]) != int(player_id):
            log_security_event(
                event_type="score_rejected",
                ip_address=ip_address,
                user_id=player_id,
                role=current_user["role"],
                success=False,
                reason="session_owner_mismatch",
                extra={"target_player_id": int(partida["jugador_id"])},
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puede registrar puntajes para otra partida.",
            )

        if partida["usado"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La partida ya fue usada para registrar puntaje.",
            )

        partida_id = partida["id"]

        await execute(
            """
            UPDATE partidas
            SET usado = TRUE, ended_at = NOW()
            WHERE id = $1
            """,
            partida_id,
        )

    row = await fetchrow(
        """
        INSERT INTO puntuaciones(jugador_id, partida_id, score, level_reached, estado)
        VALUES($1, $2, $3, $4, 'valida')
        RETURNING id, jugador_id, score, level_reached, estado, created_at
        """,
        player_id,
        partida_id,
        body.score,
        body.level_reached,
    )

    log_security_event(
        event_type="score_registered",
        ip_address=ip_address,
        user_id=player_id,
        role=current_user["role"],
        success=True,
        reason="score_saved",
        extra={
            "score": body.score,
            "level_reached": body.level_reached,
            "partida_id": partida_id,
        },
    )

    return {
        "message": "Puntaje registrado correctamente.",
        "score": {
            "id": row["id"],
            "score": row["score"],
            "level_reached": row["level_reached"],
            "estado": row["estado"],
            "created_at": str(row["created_at"]),
        },
    }


@router.post("/end", status_code=status.HTTP_201_CREATED)
async def end_game(
    body: ScoreBody,
    request: Request,
    current_user: dict = Depends(require_role("jugador")),
):
    """
    Alias de compatibilidad para clientes que llamen /game/end.
    """
    return await register_score(body, request, current_user)