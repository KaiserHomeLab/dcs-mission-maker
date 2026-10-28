"""The app icon (tray and .exe), drawn in code: an amber jet on the dark theme panel."""
from PIL import Image, ImageDraw

BG, JET = (23, 32, 39, 255), (224, 165, 38, 255)
# Right half of a top-down jet in a unit square; mirrored for the left half.
_HALF = [(0.50, 0.08), (0.555, 0.26), (0.57, 0.42), (0.92, 0.62), (0.92, 0.69), (0.57, 0.61),
         (0.555, 0.76), (0.72, 0.86), (0.72, 0.91), (0.50, 0.87)]
_JET = _HALF + [(1 - x, y) for x, y in reversed(_HALF[1:-1])]


def draw(size=256):
    big = size * 4  # draw large, then shrink: smooth edges
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, big - 1, big - 1), radius=big // 5, fill=BG)
    d.polygon([(x * big, y * big) for x, y in _JET], fill=JET)
    return img.resize((size, size), Image.LANCZOS)


def save_ico(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    draw(256).save(path, sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    return str(path)
