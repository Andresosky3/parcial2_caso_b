from fastapi import APIRouter, Header, HTTPException
import sqlite3, time, uuid
from src.auth.service import decode_token

router = APIRouter()

@router.post("/start")
def iniciar_partida(authorization: str = Header(None)):
    if not authorization: raise HTTPException(401, "Token requerido")
    payload = decode_token(authorization)
    token = str(uuid.uuid4())
    conn = sqlite3.connect("game.db")
    conn.execute(
        "INSERT INTO partidas (session_token, jugador_id, started_at) VALUES (?,?,?)",
        (token, payload["player_id"], time.time())
    )
    conn.commit(); conn.close()
    return {"session_token": token}

@router.post("/end")
def registrar_puntuacion(data: dict, authorization: str = Header(None)):
    if not authorization: raise HTTPException(401, "Token requerido")
    try: payload = decode_token(authorization)
    except: raise HTTPException(401, "Token invalido")

    # ← VULNERABLE: acepta el score calculado por el cliente
    score         = data.get("score", 0)
    session_token = data.get("session_token", "")
    level_reached = data.get("level_reached", 1)

    conn = sqlite3.connect("game.db")
    partida = conn.execute(
        "SELECT usado, jugador_id FROM partidas WHERE session_token=?", (session_token,)
    ).fetchone()
    if not partida: conn.close(); raise HTTPException(400, "Sesion invalida")
    if partida[0]: conn.close(); raise HTTPException(400, "Sesion ya registrada")
    # ← VULNERABLE: no verifica que session_token pertenezca al player_id del JWT

    conn.execute(
        "INSERT INTO puntuaciones (jugador_id, score, level_reached, estado, created_at) VALUES (?,?,?,'valida',?)",
        (payload["player_id"], score, level_reached, time.time())
    )
    conn.execute("UPDATE partidas SET usado=1 WHERE session_token=?", (session_token,))
    conn.commit(); conn.close()
    return {"mensaje": "Puntuacion registrada", "score": score}
