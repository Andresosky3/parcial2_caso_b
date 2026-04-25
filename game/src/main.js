import { GameApiService } from './api/game-api.service.js';

// ← VULNERABLE: instancia global del servicio accesible desde consola
window.gameApi = new GameApiService();

const config = {
  type: Phaser.AUTO,
  width: 800, height: 450,
  backgroundColor: '#1a1a2e',
  physics: { default: 'arcade', arcade: { gravity: { y: 500 }, debug: false } },
  scene: []  // escenas registradas aquí
};

const game = new Phaser.Game(config);
