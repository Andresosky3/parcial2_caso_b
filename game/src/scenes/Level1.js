export class Level1Scene extends Phaser.Scene {
  constructor() { super({ key: 'Level1' }); }
  score = 0; coins = 0; timeLeft = 90;

  preload() {
    // Los estudiantes deben agregar sus assets aqui
    // this.load.image('player', 'assets/sprites/player.png');
  }

  create() {
    // TODO: implementar el nivel 1 con Phaser.js
    // - Plataformas
    // - Personaje con movimiento y salto
    // - Monedas coleccionables
    // - Un tipo de enemigo basico
    // - Temporizador

    this.add.text(10, 10, 'Nivel 1 — En construccion', { color: '#fff' });

    // Al completar el nivel -> ir a Level2 y pasar el puntaje acumulado
    // this.scene.start('Level2', { accumulatedScore: this.score });
  }

  update() {}
}
