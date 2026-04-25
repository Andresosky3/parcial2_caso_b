"""Tests del anti-cheat — completar en el Parcial 2 Parte 1"""
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_score_sin_session_token():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/game/end",
            json={"score": 99999, "level_reached": 3, "session_token": ""},
            headers={"Authorization": "Bearer FAKE_TOKEN"}
        )
    assert resp.status_code in [400, 401]

@pytest.mark.asyncio
async def test_score_calculado_en_cliente():
    # TODO: verificar que el backend rechaza el campo "score" y lo recalcula
    # ACTUALMENTE el backend acepta el score del cliente — este test FALLA
    pass

@pytest.mark.asyncio
async def test_idor_historial():
    # TODO: verificar que un jugador no puede ver el historial de otro
    pass
