"""Particle system for Thanos snap disintegration effect."""
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QColor
import random
import math

class Particle:
    """Individual particle in the disintegration effect."""

    def __init__(self, x, y, color):
        """Initialize particle.

        Args:
            x: Initial X position
            y: Initial Y position
            color: QColor of the particle
        """
        self.x = float(x)
        self.y = float(y)
        self.color = color  # QColor
        self.alpha = 255

        # Random velocity (outward scatter from center)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.5, 3.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - random.uniform(1, 3)  # Upward bias

        # Lifetime
        self.life = 1.0  # 1.0 = fully alive, 0.0 = dead
        self.fade_rate = random.uniform(0.015, 0.025)  # Per frame

    def update(self):
        """Update particle position and lifetime."""
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1  # Gravity
        self.life -= self.fade_rate
        self.alpha = int(max(0, self.life * 255))

    def is_alive(self):
        """Check if particle is still visible.

        Returns:
            True if particle life > 0
        """
        return self.life > 0

class ParticleSystem(QObject):
    """Manages particle emission and animation for disintegration effect."""

    animation_complete = pyqtSignal()
    particles_updated = pyqtSignal(list)  # Emits particle list for rendering

    def __init__(self, sprite, origin_x, origin_y, config):
        """Initialize particle system.

        Args:
            sprite: QPixmap sprite to sample pixels from
            origin_x: X position of sprite
            origin_y: Y position of sprite
            config: Configuration object
        """
        super().__init__()
        self.particles = []
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.config = config

        # Generate particles from sprite
        self._generate_particles_from_sprite(sprite)

        # Update timer (30 FPS for smooth particle motion)
        self.update_timer = QTimer()
        self.update_timer.setInterval(33)  # ~30 FPS
        self.update_timer.timeout.connect(self._update_particles)

    def _generate_particles_from_sprite(self, sprite):
        """Sample sprite pixels to create particles.

        Args:
            sprite: QPixmap to sample
        """
        image = sprite.toImage()
        width = image.width()
        height = image.height()

        target_count = self.config.particle_count_target
        total_pixels = width * height
        sample_rate = max(1, total_pixels // target_count)

        for y in range(0, height, 2):  # Sample every 2 pixels
            for x in range(0, width, 2):
                if random.random() > (1.0 / sample_rate):
                    continue

                color = QColor(image.pixel(x, y))
                if color.alpha() > 50:  # Skip mostly transparent pixels
                    particle = Particle(
                        self.origin_x + x,
                        self.origin_y + y,
                        color
                    )
                    self.particles.append(particle)

        print(f"[PARTICLES] Generated {len(self.particles)} particles")

    def start(self):
        """Start particle animation."""
        if self.particles:
            self.update_timer.start()
            print("[PARTICLES] Animation started")

    def _update_particles(self):
        """Update all particles and check for completion."""
        # Update each particle
        for particle in self.particles:
            particle.update()

        # Remove dead particles
        self.particles = [p for p in self.particles if p.is_alive()]

        # Emit updated particle list for rendering
        self.particles_updated.emit(self.particles)

        # Check if animation complete
        if not self.particles:
            self.update_timer.stop()
            print("[PARTICLES] Animation complete")
            self.animation_complete.emit()

    def stop(self):
        """Stop particle animation immediately."""
        self.update_timer.stop()
        self.particles.clear()
        print("[PARTICLES] Animation stopped")
