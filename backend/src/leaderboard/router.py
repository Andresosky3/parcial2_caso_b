"""Leaderboard seguro para PixelForge Studio."""

import sqlite3
from html import escape

from fastapi import APIRouter, Query

router = APIRouter()

DB_PATH = "game.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/leaderboard")
def leaderboard(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Cantidad máxima de posiciones a consultar. Máximo permitido: 50."
    )
):
    """
    Consulta el ranking global de jugadores.

    Controles implementados:
    - limit validado con mínimo 1 y máximo 50.
    - consulta SQL parametrizada.
    - solo se muestran puntuaciones con estado 'valida'.
    - se escapa nickname antes de responder para reducir riesgo de XSS reflejado.
    """
    conn = get_conn()

    try:
        rows = conn.execute(
            """
            SELECT
                j.nickname AS nickname,
                MAX(p.score) AS best,
                MAX(p.level_reached) AS lvl
            FROM puntuaciones p
            JOIN jugadores j ON j.id = p.jugador_id
            WHERE p.estado = ?
            GROUP BY j.id, j.nickname
            ORDER BY best DESC
            LIMIT ?
            """,
            ("valida", limit),
        ).fetchall()

        rankings = []

        for index, row in enumerate(rows, start=1):
            rankings.append(
                {
                    "position": index,
                    "nickname": escape(row["nickname"]),
                    "score": int(row["best"]),
                    "level_reached": int(row["lvl"]),
                }
            )

        return {
            "limit": limit,
            "rankings": rankings,
        }

    finally:
        conn.close()