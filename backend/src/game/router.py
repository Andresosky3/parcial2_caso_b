"""Rutas seguras de juego y anti-cheat para PixelForge Studio."""

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from src.auth.rbac import verify_role

router = APIRouter()

DB_PATH = "game.db"
MAX_SESSION_MINUTES = 30


class EndGameBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_token: str = Field(..., min_length=20, max_length=80)
    level_reached: int = Field(..., ge=1, le=10)
    coins_collected: int = Field(default=0, ge=0, le=500)
    enemies_defeated: int = Field(default=0, ge=0, le=200)
    time_remaining: int = Field(default=0, ge=0, le=600)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


def init_anticheat_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS log_anticheat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jugador_id INTEGER,
            ip_address TEXT,
            datos_enviados TEXT,
            razon_rechazo TEXT,
            timestamp TEXT NOT NULL
        )
        """
    )
    conn.commit()


def log_rechazo(
    conn: sqlite3.Connection,
    jugador_id: int,
    request: Request,
    datos: Dict,
    razon: str,
) -> None:
    init_anticheat_table(conn)

    conn.execute(
        """
        INSERT INTO log_anticheat (
            jugador_id,
            ip_address,
            datos_enviados,
            razon_rechazo,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            jugador_id,
            client_ip(request),
            json.dumps(datos, ensure_ascii=False),
            razon,
            now_iso(),
        ),
    )
    conn.commit()


def parse_datetime(value) -> datetime:
    """
    Convierte started_at a datetime.
    Soporta fechas ISO y valores numéricos heredados.
    """
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)

    text = str(value)

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromtimestamp(float(text), tz=timezone.utc)
        except ValueError:
            return datetime.now(timezone.utc)


def calculate_score(body: EndGameBody) -> int:
    """
    Calcula el score en el backend.
    El cliente NO envía score final, solo estadísticas limitadas.
    """
    base = body.level_reached * 1000
    coins = body.coins_collected * 10
    enemies = body.enemies_defeated * 50
    time_bonus = body.time_remaining * 2

    return base + coins + enemies + time_bonus


@router.post("/start")
def iniciar_partida(
    payload: Dict = Depends(verify_role("JUGADOR")),
):
    """
    Crea una sesión de juego asociada al jugador autenticado.
    """
    jugador_id = int(payload.get("player_id") or payload.get("sub"))
    session_token = str(uuid.uuid4())

    conn = get_conn()

    try:
        conn.execute(
            """
            INSERT INTO partidas (
                session_token,
                jugador_id,
                started_at,
                usado
            )
            VALUES (?, ?, ?, ?)
            """,
            (session_token, jugador_id, now_iso(), 0),
        )

        conn.commit()

        return {
            "session_token": session_token
        }

    finally:
        conn.close()


@router.post("/end")
def registrar_puntuacion(
    body: EndGameBody,
    request: Request,
    payload: Dict = Depends(verify_role("JUGADOR")),
):
    """
    Registra la puntuación de una partida.

    Controles anti-cheat:
    - No acepta score enviado por el cliente.
    - Verifica que la sesión exista.
    - Verifica que la sesión pertenezca al jugador del JWT.
    - Verifica que la sesión no haya sido usada.
    - Valida duración máxima de sesión.
    - Calcula score en backend.
    - Registra rechazos en log_anticheat.
    """
    jugador_id = int(payload.get("player_id") or payload.get("sub"))

    raw_body = body.model_dump()

    conn = get_conn()

    try:
        partida = conn.execute(
            """
            SELECT
                id,
                usado,
                jugador_id,
                started_at
            FROM partidas
            WHERE session_token = ?
            """,
            (body.session_token,),
        ).fetchone()

        if not partida:
            log_rechazo(
                conn,
                jugador_id,
                request,
                raw_body,
                "session_token_inexistente",
            )
            raise HTTPException(
                status_code=400,
                detail="Sesión inválida."
            )

        if int(partida["jugador_id"]) != jugador_id:
            log_rechazo(
                conn,
                jugador_id,
                request,
                raw_body,
                "session_token_no_pertenece_al_jugador",
            )
            raise HTTPException(
                status_code=403,
                detail="No tienes permiso para registrar esta sesión."
            )

        if bool(partida["usado"]):
            log_rechazo(
                conn,
                jugador_id,
                request,
                raw_body,
                "session_token_reutilizado",
            )
            raise HTTPException(
                status_code=400,
                detail="La sesión ya fue registrada."
            )

        started_at = parse_datetime(partida["started_at"])
        session_age = datetime.now(timezone.utc) - started_at

        if session_age > timedelta(minutes=MAX_SESSION_MINUTES):
            log_rechazo(
                conn,
                jugador_id,
                request,
                raw_body,
                "session_expirada",
            )
            raise HTTPException(
                status_code=400,
                detail="La sesión expiró."
            )

        calculated_score = calculate_score(body)

        conn.execute(
            """
            INSERT INTO puntuaciones (
                jugador_id,
                partida_id,
                score,
                level_reached,
                coins_collected,
                time_remaining,
                estado,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                jugador_id,
                partida["id"],
                calculated_score,
                body.level_reached,
                body.coins_collected,
                body.time_remaining,
                "valida",
                now_iso(),
            ),
        )

        conn.execute(
            """
            UPDATE partidas
            SET usado = ?,
                ended_at = ?
            WHERE id = ?
            """,
            (1, now_iso(), partida["id"]),
        )

        conn.commit()

        return {
            "mensaje": "Puntuación registrada.",
            "score": calculated_score,
            "level_reached": body.level_reached,
        }

    finally:
        conn.close()