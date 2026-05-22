"""Servicio MFA TOTP para PixelForge Studio."""

import base64
import hashlib
import io
import os
from typing import Optional

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken

from src.settings import get_settings


MFA_ISSUER = os.getenv("MFA_ISSUER", "PixelForge Studio")


def get_fernet() -> Fernet:
    """
    Crea una llave Fernet para cifrar secretos MFA.

    Si existe MFA_ENCRYPTION_KEY se usa directamente.
    Si no existe, se deriva desde JWT_SECRET_KEY para ambiente local.
    """
    raw_key = os.getenv("MFA_ENCRYPTION_KEY")

    if raw_key:
        return Fernet(raw_key.encode())

    settings = get_settings()
    source = settings.jwt_secret_key or os.getenv("JWT_SECRET_KEY", "local-dev-secret")
    derived_key = base64.urlsafe_b64encode(
        hashlib.sha256(source.encode()).digest()
    )

    return Fernet(derived_key)


def generate_totp_secret() -> str:
    """Genera secreto TOTP compatible con Google Authenticator."""
    return pyotp.random_base32()


def encrypt_mfa_secret(secret: str) -> str:
    """Cifra el secreto MFA antes de guardarlo."""
    return get_fernet().encrypt(secret.encode()).decode()


def decrypt_mfa_secret(encrypted_secret: str) -> str:
    """Descifra el secreto MFA."""
    try:
        return get_fernet().decrypt(encrypted_secret.encode()).decode()
    except InvalidToken:
        raise ValueError("No fue posible descifrar el secreto MFA.")


def build_provisioning_uri(secret: str, email: str) -> str:
    """Construye URI otpauth para apps autenticadoras."""
    return pyotp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=MFA_ISSUER,
    )


def verify_totp_code(secret: str, code: str) -> bool:
    """Verifica código TOTP de 6 dígitos."""
    clean_code = code.replace(" ", "").strip()

    if not clean_code.isdigit():
        return False

    return pyotp.TOTP(secret).verify(clean_code, valid_window=1)


def generate_qr_png_base64(provisioning_uri: str) -> str:
    """Genera QR PNG en base64 para mostrarlo en frontend o evidencia."""
    qr = qrcode.QRCode(
        version=1,
        box_size=8,
        border=2,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")

    return base64.b64encode(buffer.getvalue()).decode()