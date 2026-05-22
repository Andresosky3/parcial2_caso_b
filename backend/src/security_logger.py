"""Logger de eventos de seguridad para PixelForge Studio.

Estos logs se diseñan para ser recolectados posteriormente por Wazuh Agent.
El formato usado es JSON Lines: un evento JSON por línea.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
DEFAULT_LOG_PATH = DEFAULT_LOG_DIR / "security.log"

SECURITY_LOG_PATH = Path(os.getenv("SECURITY_LOG_FILE", str(DEFAULT_LOG_PATH)))
SECURITY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


security_logger = logging.getLogger("pixelforge_security")
security_logger.setLevel(logging.INFO)
security_logger.propagate = False

if not security_logger.handlers:
    file_handler = logging.FileHandler(SECURITY_LOG_PATH, encoding="utf-8")
    formatter = logging.Formatter("%(message)s")
    file_handler.setFormatter(formatter)
    security_logger.addHandler(file_handler)


def log_security_event(
    event_type: str,
    ip_address: Optional[str] = None,
    user_email: Optional[str] = None,
    user_id: Optional[int] = None,
    role: Optional[str] = None,
    success: Optional[bool] = None,
    reason: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Registra un evento de seguridad en formato JSON Lines."""

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "ip_address": ip_address,
        "user_email": user_email,
        "user_id": user_id,
        "role": role,
        "success": success,
        "reason": reason,
        "extra": extra or {},
    }

    security_logger.info(json.dumps(payload, ensure_ascii=False))
