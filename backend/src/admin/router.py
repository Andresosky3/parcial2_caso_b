from fastapi import APIRouter, Header, HTTPException
import sqlite3
from src.auth.service import decode_token

router = APIRouter()

@router.delete("/puntuacion/{score_id}")
def eliminar_puntuacion(score_id: int, authorization: str = Header(None)):
    if not authorization: raise HTTPException(401, "Token requerido")
    try: payload = decode_token(authorization)
    except: raise HTTPException(401, "Token invalido")
    # ← VULNERABLE: no verifica rol ADMIN/MODERADOR
    conn = sqlite3.connect("game.db")
    # ← VULNERABLE: DELETE real — deberia marcar estado='invalidada'
    conn.execute(f"DELETE FROM puntuaciones WHERE id = {score_id}")
    conn.commit(); conn.close()
    return {"mensaje": f"Puntuacion {score_id} eliminada"}

@router.get("/jugador/{player_id}/historial")
def historial(player_id: int, authorization: str = Header(None)):
    if not authorization: raise HTTPException(401, "Token requerido")
    payload = decode_token(authorization)
    # ← VULNERABLE: IDOR — no verifica player_id del path vs JWT
    conn = sqlite3.connect("game.db")
    rows = conn.execute(
        "SELECT score, level_reached, created_at FROM puntuaciones WHERE jugador_id=?",
        (player_id,)
    ).fetchall()
    conn.close()
    return {"historial": rows}
