"""Sistema de tarjetas simuladas, tokens e ítems para PixelForge Studio."""

from datetime import datetime
from typing import Dict
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.auth.rbac import require_role
from src.db import fetch, fetchrow, get_pool
from src.security_logger import log_security_event


router = APIRouter(tags=["payments"])


TOKEN_PACKAGES: Dict[str, Dict[str, int | str]] = {
    "starter": {
        "name": "Paquete Starter",
        "tokens": 100,
        "price_cop": 5000,
    },
    "pro": {
        "name": "Paquete Pro",
        "tokens": 250,
        "price_cop": 10000,
    },
    "legend": {
        "name": "Paquete Legend",
        "tokens": 600,
        "price_cop": 20000,
    },
}


ITEM_CATALOG: Dict[str, Dict[str, int | str]] = {
    "skin_neon": {
        "name": "Skin Neon",
        "price_tokens": 80,
    },
    "avatar_dragon": {
        "name": "Avatar Dragón",
        "price_tokens": 120,
    },
    "boost_xp": {
        "name": "Boost XP",
        "price_tokens": 200,
    },
}


class RegisterCardBody(BaseModel):
    """
    Registro de tarjeta simulada.

    Seguridad:
    - No se guarda card_number completo.
    - No se guarda CVV.
    - Solo se guarda card_token, last4, brand y vencimiento.
    """

    model_config = ConfigDict(extra="forbid")

    card_number: str = Field(min_length=16, max_length=16)
    holder_name: str = Field(min_length=3, max_length=80)
    exp_month: int = Field(ge=1, le=12)
    exp_year: int = Field(ge=2026, le=2040)
    cvv: str = Field(min_length=3, max_length=4)

    @field_validator("card_number")
    @classmethod
    def validate_card_number_digits(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("La tarjeta debe contener solo números.")
        return value

    @field_validator("cvv")
    @classmethod
    def validate_cvv_digits(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("CVV inválido.")
        return value


class PurchaseTokensBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_token: str
    package_code: str = Field(min_length=3, max_length=30)


class BuyItemBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_code: str = Field(min_length=3, max_length=50)


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


def luhn_is_valid(card_number: str) -> bool:
    """Valida número de tarjeta con algoritmo Luhn."""
    digits = [int(char) for char in card_number]
    checksum = 0
    parity = len(digits) % 2

    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit

    return checksum % 10 == 0


def detect_card_brand(card_number: str) -> str:
    """Detecta marca de tarjeta de forma básica."""
    if card_number.startswith("4"):
        return "visa"

    if card_number[:2] in {"51", "52", "53", "54", "55"}:
        return "mastercard"

    if card_number.startswith(("34", "37")):
        return "amex"

    return "unknown"


def validate_expiration(exp_month: int, exp_year: int) -> None:
    """Valida que la tarjeta simulada no esté vencida."""
    now = datetime.utcnow()
    current_year = now.year
    current_month = now.month

    if exp_year < current_year or (exp_year == current_year and exp_month < current_month):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La tarjeta simulada está vencida.",
        )


@router.get("/payments/packages")
async def list_token_packages():
    """Lista paquetes de tokens definidos en backend."""
    return {
        "packages": [
            {
                "code": code,
                "name": package["name"],
                "tokens": package["tokens"],
                "price_cop": package["price_cop"],
            }
            for code, package in TOKEN_PACKAGES.items()
        ]
    }


@router.get("/store/items")
async def list_store_items():
    """Lista catálogo de ítems definido en backend."""
    return {
        "items": [
            {
                "code": code,
                "name": item["name"],
                "price_tokens": item["price_tokens"],
            }
            for code, item in ITEM_CATALOG.items()
        ]
    }


@router.get("/payments/wallet")
async def get_wallet(current_user: dict = Depends(require_role("jugador"))):
    """Consulta saldo de tokens del jugador autenticado."""
    row = await fetchrow(
        """
        SELECT token_balance
        FROM jugadores
        WHERE id = $1
        """,
        current_user["id"],
    )

    return {
        "user_id": current_user["id"],
        "token_balance": int(row["token_balance"] if row else 0),
    }


@router.post("/payments/cards", status_code=status.HTTP_201_CREATED)
async def register_card(
    body: RegisterCardBody,
    request: Request,
    current_user: dict = Depends(require_role("jugador")),
):
    """Registra una tarjeta simulada tokenizada."""

    ip_address = get_client_ip(request)
    player_id = current_user["id"]

    if not luhn_is_valid(body.card_number):
        log_security_event(
            event_type="card_register_failed",
            ip_address=ip_address,
            user_id=player_id,
            role=current_user["role"],
            success=False,
            reason="invalid_luhn",
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tarjeta simulada inválida.",
        )

    validate_expiration(body.exp_month, body.exp_year)

    cards_count = await fetchrow(
        """
        SELECT COUNT(*) AS total
        FROM payment_cards
        WHERE jugador_id = $1
          AND status = 'activa'
        """,
        player_id,
    )

    if int(cards_count["total"]) >= 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo puede registrar máximo 2 tarjetas simuladas.",
        )

    card_token = uuid4()
    last4 = body.card_number[-4:]
    brand = detect_card_brand(body.card_number)

    row = await fetchrow(
        """
        INSERT INTO payment_cards(jugador_id, card_token, last4, brand, exp_month, exp_year, status)
        VALUES($1, $2, $3, $4, $5, $6, 'activa')
        RETURNING card_token, last4, brand, exp_month, exp_year, status, created_at
        """,
        player_id,
        card_token,
        last4,
        brand,
        body.exp_month,
        body.exp_year,
    )

    log_security_event(
        event_type="card_registered",
        ip_address=ip_address,
        user_id=player_id,
        role=current_user["role"],
        success=True,
        reason="simulated_card_tokenized",
        extra={
            "last4": last4,
            "brand": brand,
        },
    )

    return {
        "message": "Tarjeta simulada registrada correctamente.",
        "card": {
            "card_token": str(row["card_token"]),
            "last4": row["last4"],
            "brand": row["brand"],
            "exp_month": row["exp_month"],
            "exp_year": row["exp_year"],
            "status": row["status"],
            "created_at": str(row["created_at"]),
        },
    }


@router.get("/payments/cards")
async def list_cards(current_user: dict = Depends(require_role("jugador"))):
    """Lista tarjetas simuladas sin exponer número completo ni CVV."""
    rows = await fetch(
        """
        SELECT card_token, last4, brand, exp_month, exp_year, status, created_at
        FROM payment_cards
        WHERE jugador_id = $1
        ORDER BY created_at DESC
        """,
        current_user["id"],
    )

    return {
        "cards": [
            {
                "card_token": str(row["card_token"]),
                "last4": row["last4"],
                "brand": row["brand"],
                "exp_month": row["exp_month"],
                "exp_year": row["exp_year"],
                "status": row["status"],
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]
    }


@router.post("/payments/tokens/purchase", status_code=status.HTTP_201_CREATED)
async def purchase_tokens(
    body: PurchaseTokensBody,
    request: Request,
    current_user: dict = Depends(require_role("jugador")),
):
    """
    Compra simulada de tokens.

    Seguridad:
    - El precio no viene del cliente.
    - El paquete se define en backend.
    - El saldo se incrementa dentro de una transacción.
    """

    ip_address = get_client_ip(request)
    player_id = current_user["id"]

    package = TOKEN_PACKAGES.get(body.package_code)

    if not package:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paquete de tokens inválido.",
        )

    try:
        parsed_card_token = UUID(body.card_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de tarjeta inválido.",
        )

    pool = get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            card = await conn.fetchrow(
                """
                SELECT id, last4, status
                FROM payment_cards
                WHERE card_token = $1
                  AND jugador_id = $2
                """,
                parsed_card_token,
                player_id,
            )

            if not card or card["status"] != "activa":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tarjeta simulada no encontrada.",
                )

            # Simulación de rechazo controlado.
            # Si last4 termina en 0000, simulamos rechazo.
            if card["last4"] == "0000":
                await conn.execute(
                    """
                    INSERT INTO token_transactions(
                        jugador_id, card_id, transaction_type, package_name,
                        tokens_amount, price_cop, result, last4
                    )
                    VALUES($1, $2, 'purchase', $3, $4, $5, 'rejected', $6)
                    """,
                    player_id,
                    card["id"],
                    body.package_code,
                    int(package["tokens"]),
                    int(package["price_cop"]),
                    card["last4"],
                )

                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Compra simulada rechazada.",
                )

            wallet = await conn.fetchrow(
                """
                UPDATE jugadores
                SET token_balance = token_balance + $1
                WHERE id = $2
                RETURNING token_balance
                """,
                int(package["tokens"]),
                player_id,
            )

            await conn.execute(
                """
                INSERT INTO token_transactions(
                    jugador_id, card_id, transaction_type, package_name,
                    tokens_amount, price_cop, result, last4
                )
                VALUES($1, $2, 'purchase', $3, $4, $5, 'approved', $6)
                """,
                player_id,
                card["id"],
                body.package_code,
                int(package["tokens"]),
                int(package["price_cop"]),
                card["last4"],
            )

    log_security_event(
        event_type="tokens_purchased",
        ip_address=ip_address,
        user_id=player_id,
        role=current_user["role"],
        success=True,
        reason="simulated_purchase_approved",
        extra={
            "package_code": body.package_code,
            "tokens": int(package["tokens"]),
            "price_cop": int(package["price_cop"]),
        },
    )

    return {
        "message": "Compra simulada aprobada.",
        "package": {
            "code": body.package_code,
            "name": package["name"],
            "tokens": package["tokens"],
            "price_cop": package["price_cop"],
        },
        "token_balance": wallet["token_balance"],
    }


@router.post("/store/items/buy", status_code=status.HTTP_201_CREATED)
async def buy_item(
    body: BuyItemBody,
    request: Request,
    current_user: dict = Depends(require_role("jugador")),
):
    """
    Compra de ítems con tokens.

    Seguridad:
    - El precio no viene del cliente.
    - El catálogo se define en backend.
    - Se usa transacción y bloqueo de fila para evitar saldo negativo.
    """

    ip_address = get_client_ip(request)
    player_id = current_user["id"]

    item = ITEM_CATALOG.get(body.item_code)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ítem inválido.",
        )

    item_price = int(item["price_tokens"])
    pool = get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            wallet = await conn.fetchrow(
                """
                SELECT token_balance
                FROM jugadores
                WHERE id = $1
                FOR UPDATE
                """,
                player_id,
            )

            if not wallet:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Jugador no encontrado.",
                )

            if int(wallet["token_balance"]) < item_price:
                await conn.execute(
                    """
                    INSERT INTO token_transactions(
                        jugador_id, transaction_type, item_code,
                        tokens_amount, price_cop, result
                    )
                    VALUES($1, 'spend', $2, $3, 0, 'rejected')
                    """,
                    player_id,
                    body.item_code,
                    item_price,
                )

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Saldo insuficiente de tokens.",
                )

            updated_wallet = await conn.fetchrow(
                """
                UPDATE jugadores
                SET token_balance = token_balance - $1
                WHERE id = $2
                RETURNING token_balance
                """,
                item_price,
                player_id,
            )

            await conn.execute(
                """
                INSERT INTO player_items(jugador_id, item_code, item_name, tokens_spent)
                VALUES($1, $2, $3, $4)
                """,
                player_id,
                body.item_code,
                str(item["name"]),
                item_price,
            )

            await conn.execute(
                """
                INSERT INTO token_transactions(
                    jugador_id, transaction_type, item_code,
                    tokens_amount, price_cop, result
                )
                VALUES($1, 'spend', $2, $3, 0, 'approved')
                """,
                player_id,
                body.item_code,
                item_price,
            )

    log_security_event(
        event_type="item_purchased",
        ip_address=ip_address,
        user_id=player_id,
        role=current_user["role"],
        success=True,
        reason="tokens_spent",
        extra={
            "item_code": body.item_code,
            "tokens_spent": item_price,
        },
    )

    return {
        "message": "Ítem comprado correctamente.",
        "item": {
            "code": body.item_code,
            "name": item["name"],
            "tokens_spent": item_price,
        },
        "token_balance": updated_wallet["token_balance"],
    }


@router.get("/payments/transactions")
async def list_transactions(current_user: dict = Depends(require_role("jugador"))):
    """Lista historial de transacciones del jugador."""
    rows = await fetch(
        """
        SELECT transaction_type, package_name, item_code, tokens_amount,
               price_cop, result, last4, created_at
        FROM token_transactions
        WHERE jugador_id = $1
        ORDER BY created_at DESC
        LIMIT 50
        """,
        current_user["id"],
    )

    return {
        "transactions": [
            {
                "transaction_type": row["transaction_type"],
                "package_name": row["package_name"],
                "item_code": row["item_code"],
                "tokens_amount": row["tokens_amount"],
                "price_cop": row["price_cop"],
                "result": row["result"],
                "last4": row["last4"],
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]
    }
