"""Tests de auth para Caso B"""
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_login_sql_injection():
    # Prueba que SQL injection en login sea bloqueado por prepared statements
    # ACTUALMENTE es VULNERABLE — este test documenta la falla
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/auth/login", json={
            "email": "' OR '1'='1",
            "password": "cualquiera"
        })
    # Con SQL injection el atacante podria loguearse — despues de corregir debe ser 401/422
    assert resp.status_code in [401, 422]
