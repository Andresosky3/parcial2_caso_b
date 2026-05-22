"""Módulo de conexión PostgreSQL con asyncpg."""

from typing import Optional

import asyncpg

from src.settings import get_settings


_pool: Optional[asyncpg.Pool] = None


async def connect_db() -> None:
    """
    Crea el pool de conexiones a PostgreSQL.
    Se ejecuta al iniciar la aplicación FastAPI.
    """
    global _pool

    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=1,
            max_size=5,
            command_timeout=30,
        )


async def disconnect_db() -> None:
    """
    Cierra el pool de conexiones a PostgreSQL.
    Se ejecuta al apagar la aplicación FastAPI.
    """
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """
    Retorna el pool activo de PostgreSQL.
    """
    if _pool is None:
        raise RuntimeError("La conexión a PostgreSQL no ha sido inicializada.")
    return _pool


async def fetchval(query: str, *args):
    """
    Ejecuta una consulta que retorna un único valor.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)


async def fetchrow(query: str, *args):
    """
    Ejecuta una consulta que retorna una fila.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetch(query: str, *args):
    """
    Ejecuta una consulta que retorna varias filas.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def execute(query: str, *args):
    """
    Ejecuta una consulta INSERT, UPDATE o DELETE.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)