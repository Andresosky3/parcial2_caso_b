"""Ranking global seguro para PixelForge Studio."""

from datetime import datetime, timedelta
from typing import Dict, Tuple

from fastapi import APIRouter, Query

from src.db import fetch, fetchval


router = APIRouter(tags=["leaderboard"])


CACHE_TTL_SECONDS = 30
_leaderboard_cache: Dict[Tuple[int, int], dict] = {}


def get_cache_key(page: int, limit: int) -> Tuple[int, int]:
    return page, limit


def is_cache_valid(cached_at: datetime) -> bool:
    return datetime.utcnow() - cached_at < timedelta(seconds=CACHE_TTL_SECONDS)


async def build_leaderboard(page: int, limit: int) -> dict:
    offset = (page - 1) * limit

    total_players = await fetchval(
        """
        SELECT COUNT(*)
        FROM (
            SELECT jugador_id
            FROM puntuaciones
            WHERE estado = 'valida'
            GROUP BY jugador_id
        ) AS grouped_scores
        """
    )

    rows = await fetch(
        """
        WITH best_scores AS (
            SELECT jugador_id, MAX(score) AS best_score
            FROM puntuaciones
            WHERE estado = 'valida'
            GROUP BY jugador_id
        ),
        ranked_scores AS (
            SELECT
                ROW_NUMBER() OVER (ORDER BY best_score DESC, j.nickname ASC) AS position,
                j.nickname AS nickname,
                best_score AS score
            FROM best_scores bs
            INNER JOIN jugadores j ON j.id = bs.jugador_id
            WHERE j.estado = 'activo'
        )
        SELECT position, nickname, score
        FROM ranked_scores
        ORDER BY position
        LIMIT $1 OFFSET $2
        """,
        limit,
        offset,
    )

    rankings = [
        {
            "position": row["position"],
            "nickname": row["nickname"],
            "score": row["score"],
        }
        for row in rows
    ]

    return {
        "page": page,
        "limit": limit,
        "total_players": int(total_players or 0),
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "cached": False,
        "rankings": rankings,
    }


@router.get("/leaderboard")
@router.get("/api/leaderboard")
async def leaderboard(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
):
    """
    Ranking público.

    Reglas:
    - No requiere autenticación.
    - No expone email.
    - No expone ID interno.
    - Implementa paginación.
    - limit máximo 50.
    - Cache TTL 30 segundos.
    """

    cache_key = get_cache_key(page, limit)
    cached = _leaderboard_cache.get(cache_key)

    if cached and is_cache_valid(cached["cached_at"]):
        data = cached["data"].copy()
        data["cached"] = True
        return data

    data = await build_leaderboard(page, limit)

    _leaderboard_cache[cache_key] = {
        "cached_at": datetime.utcnow(),
        "data": data,
    }

    return data