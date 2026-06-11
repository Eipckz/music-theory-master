"""Generate the application icon (resources/icons/icon.ico) with Pillow.

Run once before packaging:  python build/make_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "music_theory" / "resources" / "icons" / "icon.ico"
ACCENT_TOP = (91, 141, 239)
ACCENT_BOT = (63, 107, 208)


def _rounded_mask(size: int, radius_frac: float = 0.22) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    r = int(size * radius_frac)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=255)
    return mask


def _gradient(size: int) -> Image.Image:
    base = Image.new("RGB", (size, size), ACCENT_TOP)
    top, bot = ACCENT_TOP, ACCENT_BOT
    px = base.load()
    for y in range(size):
        t = y / max(1, size - 1)
        col = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        for x in range(size):
            px[x, y] = col
    return base


def _draw_note(img: Image.Image) -> None:
    size = img.width
    d = ImageDraw.Draw(img)
    s = size / 256.0
    white = (255, 255, 255)
    # stem
    stem_x = int(150 * s)
    d.rounded_rectangle([stem_x, int(58 * s), stem_x + int(14 * s), int(176 * s)],
                        radius=int(6 * s), fill=white)
    # flag
    d.polygon([(stem_x + int(14 * s), int(58 * s)),
               (stem_x + int(70 * s), int(86 * s)),
               (stem_x + int(70 * s), int(120 * s)),
               (stem_x + int(14 * s), int(92 * s))], fill=white)
    # note head
    hx, hy = int(96 * s), int(176 * s)
    d.ellipse([hx, hy, hx + int(58 * s), hy + int(42 * s)], fill=white)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    master = 256
    img = _gradient(master).convert("RGBA")
    img.putalpha(_rounded_mask(master))
    _draw_note(img)
    sizes = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]
    img.save(OUT, format="ICO", sizes=sizes)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
