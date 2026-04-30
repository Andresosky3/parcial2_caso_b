"""Rutas administrativas seguras para PixelForge Studio."""

import sqlite3
from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from src.auth.rbac import require_self_or_role, verify_role

router = APIRouter()

DB_PATH = "game.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.delete("/puntuacion/{score_id}")
def invalidar_puntuacion(
    score_id: int,
    payload: Dict = Depends(verify_role("MODERADOR")),
):
    """
    Invalida una puntuación sin eliminarla físicamente.
    Requiere rol MODERADOR o ADMIN.
    """
    conn = get_conn()

    try:
        row = conn.execute(
            """
            SELECT id, estado
            FROM puntuaciones
            WHERE id = ?
            """,
            (score_id,),
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Puntuación no encontrada."
            )

        conn.execute(
            """
            UPDATE puntuaciones
            SET estado = ?
            WHERE id = ?
            """,
            ("invalidada", score_id),
        )

        conn.commit()

        return {
            "mensaje": "Puntuación invalidada correctamente.",
            "score_id": score_id,
            "estado": "invalidada",
            "admin_user": payload.get("sub") or payload.get("player_id"),
        }

    finally:
        conn.close()


@router.get("/jugador/{player_id}/historial")
def historial_jugador(
    player_id: int,
    payload: Dict = Depends(verify_role("JUGADOR")),
):
    """
    Consulta el historial de un jugador.
    El jugador solo puede consultar su propio historial.
    ADMIN también puede consultar cualquier historial.
    """
    require_self_or_role(player_id, payload, "ADMIN")

    conn = get_conn()

    try:
        rows = conn.execute(
            """
            SELECT
                id,
                score,
                level_reached,
                estado,
                created_at
            FROM puntuaciones
            WHERE jugador_id = ?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (player_id,),
        ).fetchall()

        historial = [
            {
                "id": row["id"],
                "score": row["score"],
                "level_reached": row["level_reached"],
                "estado": row["estado"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

        return {
            "player_id": player_id,
            "historial": historial,
        }

    finally:
        conn.close()


@router.get("/puntuaciones/invalidas")
def listar_puntuaciones_invalidas(
    payload: Dict = Depends(verify_role("MODERADOR")),
):
    """
    Lista puntuaciones invalidadas.
    Requiere MODERADOR o ADMIN.
    """
    conn = get_conn()

    try:
        rows = conn.execute(
            """
            SELECT
                p.id,
                p.jugador_id,
                j.nickname,
                p.score,
                p.level_reached,
                p.estado,
                p.created_at
            FROM puntuaciones p
            JOIN jugadores j ON j.id = p.jugador_id
            WHERE p.estado = ?
            ORDER BY p.created_at DESC
            LIMIT 100
            """,
            ("invalidada",),
        ).fetchall()

        return {
            "puntuaciones": [
                {
                    "id": row["id"],
                    "jugador_id": row["jugador_id"],
                    "nickname": row["nickname"],
                    "score": row["score"],
                    "level_reached": row["level_reached"],
                    "estado": row["estado"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
        }

    finally:
        conn.close()