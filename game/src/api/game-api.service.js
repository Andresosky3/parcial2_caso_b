// Servicio de comunicación con el backend — CON VULNERABILIDADES

const API_BASE = 'https://pixelforge-grupoN.lab.umng.edu.co/api';

export class GameApiService {
  constructor() {
    // ← VULNERABLE: token en propiedad pública
    this.jwtToken = localStorage.getItem('jwt') || null;
    console.log('[DEBUG] Token cargado:', this.jwtToken);  // ← expone token en consola
  }

  async login(email, password) {
    const data = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    }).then(r => r.json());
    this.jwtToken = data.token;
    localStorage.setItem('jwt', data.token);
    return data;
  }

  async iniciarPartida() {
    return fetch(`${API_BASE}/game/start`, {
      method: 'POST',
      // ← VULNERABLE: sin prefijo Bearer
      headers: { Authorization: this.jwtToken }
    }).then(r => r.json());
  }

  async registrarPuntuacion(score, levelReached, sessionToken) {
    // ← VULNERABLE: score calculado en el cliente y enviado directamente
    const finalScore = score + (levelReached * 500);

    return fetch(`${API_BASE}/game/end`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: this.jwtToken       // ← sin Bearer
      },
      body: JSON.stringify({
        score: finalScore,                 // ← score del cliente
        level_reached: levelReached,
        session_token: sessionToken
      })
    }).then(r => r.json());
  }

  async obtenerLeaderboard() {
    // ← VULNERABLE: sin limite — descarga todo
    return fetch(`${API_BASE}/leaderboard?limit=999999`).then(r => r.json());
  }
}

// ← VULNERABLE: funcion de debug global
window.debugSetScore = (score) => {
  console.log('Forzando score:', score);
  window.gameApi.registrarPuntuacion(score, 3, 'debug-token');
};
