"""Servicio de auth — CON VULNERABILIDADES INTENCIONALES"""
import hashlib, uuid, jwt
from datetime import datetime

# ← VULNERABLE: hardcodeado
JWT_SECRET = "pixelforge123"
DB_CREDS = {"user": "admin", "password": "postgres123"}

def hash_password(password: str) -> str:
    # ← VULNERABLE: SHA1 sin sal
    return hashlib.sha1(password.encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hashlib.sha1(plain.encode()).hexdigest() == hashed

def create_token(data: dict) -> str:
    # ← VULNERABLE: sin exp ni jti
    return jwt.encode(data.copy(), JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token.replace("Bearer ", ""), JWT_SECRET, algorithms=["HS256"])
    except Exception as e:
        raise ValueError(str(e))
