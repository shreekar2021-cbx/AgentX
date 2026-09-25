from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "public" / "icons"
DEST.mkdir(parents=True, exist_ok=True)

for size in (192, 512):
    image = Image.new("RGBA", (size, size), "#0b1413")
    draw = ImageDraw.Draw(image)
    margin = size // 12
    draw.rounded_rectangle((margin, margin, size - margin, size - margin), radius=size // 5, fill="#183a2c")
    draw.ellipse((size * .24, size * .18, size * .78, size * .75), fill="#74daa0")
    draw.polygon([(size * .42, size * .69), (size * .72, size * .27), (size * .62, size * .76)], fill="#0b1413")
    draw.line((size * .27, size * .77, size * .51, size * .56), fill="#c2f5d2", width=size // 24)
    image.save(DEST / f"icon-{size}.png")
    print(DEST / f"icon-{size}.png")
