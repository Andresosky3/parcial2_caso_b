from fastapi import APIRouter, Query
import sqlite3

router = APIRouter()

@router.get("/leaderboard")
def leaderboard(limit: int = Query(default=10)):
    # ← VULNERABLE: sin limite maximo — limit=999999 descarga todo
    conn = sqlite3.connect("game.db")
    rows = conn.execute(
        f"SELECT j.nickname, MAX(p.score) as best, MAX(p.level_reached) as lvl "
        f"FROM puntuaciones p JOIN jugadores j ON j.id=p.jugador_id "
        f"WHERE p.estado='valida' GROUP BY j.id ORDER BY best DESC LIMIT {limit}"
    ).fetchall()
    conn.close()
    return {"rankings": [{"nickname": r[0], "score": r[1], "level_reached": r[2]} for r in rows]}
