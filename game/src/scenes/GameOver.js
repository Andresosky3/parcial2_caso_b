export class GameOverScene extends Phaser.Scene {
  constructor() { super({ key: 'GameOver' }); }

  async create(data) {
    const totalScore = data.score || 0;
    this.add.text(400, 150, 'GAME OVER', { fontSize: '48px', color: '#C0392B' }).setOrigin(0.5);
    this.add.text(400, 220, `Puntuacion: ${totalScore}`, { fontSize: '28px', color: '#fff' }).setOrigin(0.5);

    if (window.gameApi.jwtToken) {
      const sessionResp = await window.gameApi.iniciarPartida();
      const resultado = await window.gameApi.registrarPuntuacion(
        totalScore, data.level || 1, sessionResp.session_token
      );
      this.add.text(400, 280,
        `Tu posicion: #${resultado.rank || '?'}`,
        { fontSize: '20px', color: '#C9A84C' }
      ).setOrigin(0.5);
    }

    this.add.text(400, 360, '[ Volver al menu ]', { fontSize: '18px', color: '#aaa' })
      .setOrigin(0.5).setInteractive({ useHandCursor: true })
      .on('pointerdown', () => this.scene.start('MainMenu'));
  }
}
