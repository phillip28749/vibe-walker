"""Generate animation sprite sequences for climb_out and fade_away."""
from PIL import Image, ImageDraw
import os
import random

def create_sprite(size=64):
    """Create a base transparent image."""
    return Image.new('RGBA', (size, size), (0, 0, 0, 0))

def draw_character_body(draw, x_offset=0, y_offset=0, color=(100, 150, 255), alpha=255):
    """Draw the character's body with optional alpha."""
    color_with_alpha = color + (alpha,)
    outline_color = (80, 120, 200, alpha)

    # Head
    draw.ellipse([20+x_offset, 10+y_offset, 44+x_offset, 34+y_offset],
                 fill=color_with_alpha, outline=outline_color, width=2)

    # Body
    draw.rectangle([26+x_offset, 32+y_offset, 38+x_offset, 50+y_offset],
                   fill=color_with_alpha, outline=outline_color, width=2)

def draw_full_character(draw, x_offset=0, y_offset=0, alpha=255):
    """Draw complete character (idle pose) with optional alpha."""
    color = (100, 150, 255, alpha)

    # Body
    draw_character_body(draw, x_offset, y_offset, (100, 150, 255), alpha)

    # Arms (both down)
    draw.line([26+x_offset, 35+y_offset, 18+x_offset, 45+y_offset], fill=color, width=4)
    draw.line([38+x_offset, 35+y_offset, 46+x_offset, 45+y_offset], fill=color, width=4)

    # Legs (standing)
    draw.line([28+x_offset, 50+y_offset, 24+x_offset, 60+y_offset], fill=color, width=4)
    draw.line([36+x_offset, 50+y_offset, 40+x_offset, 60+y_offset], fill=color, width=4)

    # Eyes
    eye_color = (255, 255, 255, alpha)
    pupil_color = (0, 0, 0, alpha)
    draw.ellipse([25+x_offset, 18+y_offset, 29+x_offset, 22+y_offset], fill=eye_color)
    draw.ellipse([35+x_offset, 18+y_offset, 39+x_offset, 22+y_offset], fill=eye_color)
    draw.ellipse([26+x_offset, 19+y_offset, 28+x_offset, 21+y_offset], fill=pupil_color)
    draw.ellipse([36+x_offset, 19+y_offset, 38+x_offset, 21+y_offset], fill=pupil_color)

def generate_climb_out_sequence():
    """Generate climbing out animation sequence (8 frames)."""
    print("\nGenerating climb_out animation sequence...")

    # Create directory
    os.makedirs('sprites/climb_out', exist_ok=True)

    # 8 frames: character rises from below
    total_frames = 8
    climb_distance = 50  # Total distance to climb

    for frame in range(total_frames):
        img = create_sprite()
        draw = ImageDraw.Draw(img)

        # Calculate Y offset (starts below, ends at 0)
        progress = frame / (total_frames - 1)  # 0.0 to 1.0
        y_offset = int(climb_distance * (1 - progress))  # 50 to 0

        # Draw character at offset position
        draw_full_character(draw, x_offset=0, y_offset=y_offset, alpha=255)

        # Save frame
        filename = f'sprites/climb_out/frame_{frame:02d}.png'
        img.save(filename)
        print(f"  [OK] Created {filename} (y_offset={y_offset})")

    print(f"  Generated {total_frames} climb_out frames")

def generate_fade_away_sequence():
    """Generate fade away/disintegration animation sequence (12 frames)."""
    print("\nGenerating fade_away animation sequence...")

    # Create directory
    os.makedirs('sprites/fade_away', exist_ok=True)

    total_frames = 12

    for frame in range(total_frames):
        img = create_sprite()
        draw = ImageDraw.Draw(img)

        # Calculate alpha fade and particle dispersion
        progress = frame / (total_frames - 1)  # 0.0 to 1.0

        if progress < 0.3:
            # Frames 0-3: Normal character, slight shake
            shake_x = random.randint(-1, 1) if frame > 0 else 0
            shake_y = random.randint(-1, 1) if frame > 0 else 0
            draw_full_character(draw, x_offset=shake_x, y_offset=shake_y, alpha=255)

        elif progress < 0.6:
            # Frames 4-7: Character starts breaking apart, fading
            alpha = int(255 * (1 - (progress - 0.3) / 0.3))

            # Draw character with reduced alpha
            draw_full_character(draw, x_offset=0, y_offset=0, alpha=alpha)

            # Add scattered pixels around character
            num_particles = int(20 * ((progress - 0.3) / 0.3))
            for _ in range(num_particles):
                px = random.randint(15, 50)
                py = random.randint(10, 60)
                particle_alpha = random.randint(100, 200)
                color = (100, 150, 255, particle_alpha)
                draw.rectangle([px, py, px+2, py+2], fill=color)

        else:
            # Frames 8-11: Just scattered particles, fading out
            num_particles = int(30 * (1 - (progress - 0.6) / 0.4))
            particle_alpha = int(255 * (1 - (progress - 0.6) / 0.4))

            for _ in range(num_particles):
                px = random.randint(10, 54)
                py = random.randint(5, 60)
                size = random.randint(1, 3)
                alpha = random.randint(int(particle_alpha * 0.5), particle_alpha)
                color = (100, 150, 255, alpha)
                draw.rectangle([px, py, px+size, py+size], fill=color)

        # Save frame
        filename = f'sprites/fade_away/frame_{frame:02d}.png'
        img.save(filename)
        print(f"  [OK] Created {filename} (progress={progress:.2f})")

    print(f"  Generated {total_frames} fade_away frames")

def main():
    """Generate all animation sequences."""
    print("=" * 60)
    print("GENERATING ANIMATION SPRITE SEQUENCES")
    print("=" * 60)

    generate_climb_out_sequence()
    generate_fade_away_sequence()

    print("\n" + "=" * 60)
    print("All animation sequences generated successfully!")
    print("=" * 60)

if __name__ == '__main__':
    main()
