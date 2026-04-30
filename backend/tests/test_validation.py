"""Tests de validación y sanitización para PixelForge Studio."""

import pytest
from pydantic import ValidationError

from src.auth.router import LoginBody, RegisterBody
from src.auth.service import (
    create_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from src.game.router import EndGameBody


def test_register_body_accepts_valid_input():
    body = RegisterBody(
        nickname="Jugador_01",
        email="jugador01@example.com",
        password="Password123*"
    )

    assert body.nickname == "Jugador_01"
    assert body.email == "jugador01@example.com"


def test_register_body_rejects_invalid_nickname():
    with pytest.raises(ValidationError):
        RegisterBody(
            nickname="<script>alert(1)</script>",
            email="jugador01@example.com",
            password="Password123*"
        )


def test_register_body_rejects_extra_fields():
    with pytest.raises(ValidationError):
        RegisterBody(
            nickname="Jugador_01",
            email="jugador01@example.com",
            password="Password123*",
            role="ADMIN"
        )


def test_login_body_rejects_invalid_email():
    with pytest.raises(ValidationError):
        LoginBody(
            email="' OR '1'='1",
            password="Password123*"
        )


def test_password_strength_rejects_weak_password():
    with pytest.raises(ValueError):
        validate_password_strength("12345678")


def test_password_hash_uses_bcrypt_and_verifies():
    hashed = hash_password("Password123*")

    assert hashed != "Password123*"
    assert hashed.startswith("$2")
    assert verify_password("Password123*", hashed) is True
    assert verify_password("WrongPassword123*", hashed) is False


def test_end_game_rejects_client_score_field():
    with pytest.raises(ValidationError):
        EndGameBody(
            session_token="session-token-valid-123456789",
            level_reached=3,
            coins_collected=20,
            enemies_defeated=5,
            time_remaining=120,
            score=999999
        )


def test_end_game_rejects_out_of_range_values():
    with pytest.raises(ValidationError):
        EndGameBody(
            session_token="session-token-valid-123456789",
            level_reached=99,
            coins_collected=999999,
            enemies_defeated=5,
            time_remaining=120
        )


def test_jwt_contains_required_security_claims():
    token = create_token(
        {
            "player_id": 1,
            "nickname": "Jugador_01",
            "role": "JUGADOR"
        }
    )

    payload = decode_token(f"Bearer {token}")

    assert payload["sub"] == "1"
    assert payload["role"] == "JUGADOR"
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload