// Servicio seguro de comunicación con el backend de PixelForge Studio

const API_BASE = 'https://danielmiguel.si-umng.com/api';

export class GameApiService {
  constructor() {
    this.jwtToken = sessionStorage.getItem('jwt') || null;
  }

  getAuthHeaders() {
    if (!this.jwtToken) {
      return {};
    }

    return {
      Authorization: `Bearer ${this.jwtToken}`
    };
  }

  async handleResponse(response) {
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || 'Error en la comunicación con el servidor.');
    }

    return data;
  }

  async login(email, password) {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const data = await this.handleResponse(response);

    if (data.token) {
      this.jwtToken = data.token;
      sessionStorage.setItem('jwt', data.token);
    }

    return data;
  }

  logout() {
    this.jwtToken = null;
    sessionStorage.removeItem('jwt');
  }

  async iniciarPartida() {
    const response = await fetch(`${API_BASE}/game/start`, {
      method: 'POST',
      headers: {
        ...this.getAuthHeaders()
      }
    });

    return this.handleResponse(response);
  }

  async registrarPuntuacion(levelReached, sessionToken, stats = {}) {
    /*
      Control seguro:
      El cliente NO envía score final.
      Solo envía estadísticas limitadas.
      El backend calcula el score real.
    */
    const payload = {
      session_token: sessionToken,
      level_reached: Number(levelReached),
      coins_collected: Number(stats.coinsCollected || 0),
      enemies_defeated: Number(stats.enemiesDefeated || 0),
      time_remaining: Number(stats.timeRemaining || 0)
    };

    const response = await fetch(`${API_BASE}/game/end`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeaders()
      },
      body: JSON.stringify(payload)
    });

    return this.handleResponse(response);
  }

  async obtenerLeaderboard(limit = 10) {
    const safeLimit = Math.min(Math.max(Number(limit) || 10, 1), 50);

    const response = await fetch(`${API_BASE}/leaderboard?limit=${safeLimit}`, {
      method: 'GET'
    });

    return this.handleResponse(response);
  }
}

export const gameApi = new GameApiService();