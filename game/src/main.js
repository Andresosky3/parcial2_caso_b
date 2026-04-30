// Configuración principal del juego PixelForge Studio

const config = {
  type: Phaser.AUTO,
  width: 800,
  height: 450,
  backgroundColor: '#1a1a2e',
  physics: {
    default: 'arcade',
    arcade: {
      gravity: { y: 500 },
      debug: false
    }
  },
  scene: []
};

const game = new Phaser.Game(config);

export default game;