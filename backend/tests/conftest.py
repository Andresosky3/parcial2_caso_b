"""Configuración global de tests para PixelForge Studio."""

import os

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "pixelforge_test_secret_key_only_for_unit_tests_2026"
)