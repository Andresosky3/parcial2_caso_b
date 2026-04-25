# 🎮 Caso B — PixelForge Studio · Videojuego de Plataformas Online
## Seguridad Informática · UMNG · 2026-I

### Stack
- **Backend:** Python 3.11 + FastAPI + PostgreSQL
- **Frontend/Portal:** Angular 17
- **Juego:** Phaser.js 3.x (HTML5 Canvas)
- **Infraestructura:** AWS Lightsail (4 instancias)

### Instalación
```bash
# Backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && cp .env.example .env
uvicorn src.main:app --reload

# Portal Angular
cd frontend && npm install && ng serve

# Juego (servido por Nginx en producción — localmente abrir game/index.html)
```
