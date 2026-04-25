// TODO: implementar el personaje del juego
export class Player extends Phaser.Physics.Arcade.Sprite {
  constructor(scene, x, y) {
    super(scene, x, y, 'player');
    scene.add.existing(this);
    scene.physics.add.existing(this);
    this.setCollideWorldBounds(true);
    this.cursors = scene.input.keyboard.createCursorKeys();
  }

  update() {
    if (this.cursors.left.isDown) {
      this.setVelocityX(-200);
      this.setFlipX(true);
    } else if (this.cursors.right.isDown) {
      this.setVelocityX(200);
      this.setFlipX(false);
    } else {
      this.setVelocityX(0);
    }
    if (this.cursors.up.isDown && this.body.blocked.down) {
      this.setVelocityY(-500);
    }
  }
}
