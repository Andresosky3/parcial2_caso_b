export class MainMenuScene extends Phaser.Scene {
  constructor() { super({ key: 'MainMenu' }); }

  create() {
    this.add.text(400, 150, 'PixelForge', { fontSize: '48px', color: '#00B4D8' })
             .setOrigin(0.5);
    this.add.text(400, 220, 'Juego de Plataformas', { fontSize: '20px', color: '#fff' })
             .setOrigin(0.5);

    const btnJugar = this.add.text(400, 320, '[ JUGAR ]', { fontSize: '24px', color: '#C9A84C' })
      .setOrigin(0.5).setInteractive({ useHandCursor: true });
    btnJugar.on('pointerdown', () => this.scene.start('Level1'));

    const btnLB = this.add.text(400, 370, '[ LEADERBOARD ]', { fontSize: '18px', color: '#aaa' })
      .setOrigin(0.5).setInteractive({ useHandCursor: true });
    btnLB.on('pointerdown', () => this.scene.start('Leaderboard'));
  }
}
