"""Generate simple pixel art sprites for the vibe-walker character."""
from PIL import Image, ImageDraw

def create_sprite(size=64):
    """Create a base transparent image."""
    return Image.new('RGBA', (size, size), (0, 0, 0, 0))

def draw_character_body(draw, x_offset=0, color=(100, 150, 255)):
    """Draw the character's body (head, torso)."""
    # Head
    draw.ellipse([20+x_offset, 10, 44+x_offset, 34], fill=color, outline=(80, 120, 200), width=2)

    # Body
    draw.rectangle([26+x_offset, 32, 38+x_offset, 50], fill=color, outline=(80, 120, 200), width=2)

def draw_idle_character():
    """Create idle pose sprite (standing still)."""
    img = create_sprite()
    draw = ImageDraw.Draw(img)

    # Body
    draw_character_body(draw)

    # Arms (both down)
    draw.line([26, 35, 18, 45], fill=(100, 150, 255), width=4)  # Left arm
    draw.line([38, 35, 46, 45], fill=(100, 150, 255), width=4)  # Right arm

    # Legs (standing)
    draw.line([28, 50, 24, 60], fill=(100, 150, 255), width=4)  # Left leg
    draw.line([36, 50, 40, 60], fill=(100, 150, 255), width=4)  # Right leg

    # Eyes
    draw.ellipse([25, 18, 29, 22], fill=(255, 255, 255))
    draw.ellipse([35, 18, 39, 22], fill=(255, 255, 255))
    draw.ellipse([26, 19, 28, 21], fill=(0, 0, 0))
    draw.ellipse([36, 19, 38, 21], fill=(0, 0, 0))

    return img

def draw_walking_right_1():
    """Create walking right sprite - frame 1 (left leg forward)."""
    img = create_sprite()
    draw = ImageDraw.Draw(img)

    # Body
    draw_character_body(draw)

    # Arms (swinging)
    draw.line([26, 35, 20, 42], fill=(100, 150, 255), width=4)  # Left arm back
    draw.line([38, 35, 44, 42], fill=(100, 150, 255), width=4)  # Right arm forward

    # Legs (left forward, right back)
    draw.line([28, 50, 32, 60], fill=(100, 150, 255), width=4)  # Left leg forward
    draw.line([36, 50, 32, 60], fill=(100, 150, 255), width=4)  # Right leg back

    # Eyes looking right
    draw.ellipse([27, 18, 31, 22], fill=(255, 255, 255))
    draw.ellipse([37, 18, 41, 22], fill=(255, 255, 255))
    draw.ellipse([29, 19, 31, 21], fill=(0, 0, 0))
    draw.ellipse([39, 19, 41, 21], fill=(0, 0, 0))

    return img

def draw_walking_right_2():
    """Create walking right sprite - frame 2 (right leg forward)."""
    img = create_sprite()
    draw = ImageDraw.Draw(img)

    # Body
    draw_character_body(draw)

    # Arms (swinging opposite)
    draw.line([26, 35, 22, 42], fill=(100, 150, 255), width=4)  # Left arm forward
    draw.line([38, 35, 42, 42], fill=(100, 150, 255), width=4)  # Right arm back

    # Legs (right forward, left back)
    draw.line([28, 50, 32, 60], fill=(100, 150, 255), width=4)  # Left leg back
    draw.line([36, 50, 40, 60], fill=(100, 150, 255), width=4)  # Right leg forward

    # Eyes looking right
    draw.ellipse([27, 18, 31, 22], fill=(255, 255, 255))
    draw.ellipse([37, 18, 41, 22], fill=(255, 255, 255))
    draw.ellipse([29, 19, 31, 21], fill=(0, 0, 0))
    draw.ellipse([39, 19, 41, 21], fill=(0, 0, 0))

    return img

def flip_horizontal(img):
    """Flip image horizontally for left-facing sprites."""
    return img.transpose(Image.FLIP_LEFT_RIGHT)

def main():
    """Generate all sprite images."""
    print("Generating sprites...")

    # Create idle sprite
    idle = draw_idle_character()
    idle.save('sprites/idle.png')
    print("[OK] Created idle.png")

    # Create walking right sprites
    walk_right_1 = draw_walking_right_1()
    walk_right_1.save('sprites/walk_right_1.png')
    print("[OK] Created walk_right_1.png")

    walk_right_2 = draw_walking_right_2()
    walk_right_2.save('sprites/walk_right_2.png')
    print("[OK] Created walk_right_2.png")

    # Create walking left sprites (mirrored)
    walk_left_1 = flip_horizontal(walk_right_1)
    walk_left_1.save('sprites/walk_left_1.png')
    print("[OK] Created walk_left_1.png")

    walk_left_2 = flip_horizontal(walk_right_2)
    walk_left_2.save('sprites/walk_left_2.png')
    print("[OK] Created walk_left_2.png")

    print("\nAll sprites generated successfully!")

if __name__ == '__main__':
    main()
