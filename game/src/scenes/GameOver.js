import { gameApi } from '../api/game-api.service.js';

export class GameOverScene extends Phaser.Scene {
  constructor() {
    super({ key: 'GameOver' });
  }

  async create(data) {
    const totalScore = data.score || 0;
    const levelReached = data.level || 1;

    this.add.text(400, 150, 'GAME OVER', {
      fontSize: '48px',
      color: '#C0392B'
    }).setOrigin(0.5);

    this.add.text(400, 220, `Puntuación local: ${totalScore}`, {
      fontSize: '28px',
      color: '#fff'
    }).setOrigin(0.5);

    if (gameApi.jwtToken) {
      try {
        const sessionResp = await gameApi.iniciarPartida();

        const resultado = await gameApi.registrarPuntuacion(
          levelReached,
          sessionResp.session_token,
          {
            coinsCollected: data.coins || 0,
            enemiesDefeated: data.enemies || 0,
            timeRemaining: data.timeRemaining || 0
          }
        );

        this.add.text(
          400,
          280,
          `Score validado por servidor: ${resultado.score}`,
          {
            fontSize: '20px',
            color: '#C9A84C'
          }
        ).setOrigin(0.5);

      } catch (error) {
        this.add.text(
          400,
          280,
          'No fue posible registrar la puntuación.',
          {
            fontSize: '20px',
            color: '#C9A84C'
          }
        ).setOrigin(0.5);
      }
    }

    this.add.text(400, 360, '[ Volver al menú ]', {
      fontSize: '18px',
      color: '#aaa'
    })
      .setOrigin(0.5)
      .setInteractive({ useHandCursor: true })
      .on('pointerdown', () => this.scene.start('MainMenu'));
  }
}