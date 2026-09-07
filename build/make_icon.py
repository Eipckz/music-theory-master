"""Package the sidebar vector brand mark as the Windows application icon."""
from io import BytesIO
from pathlib import Path

from PIL import Image
from PyQt6.QtCore import QBuffer, QIODevice, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer

ICONS = Path(__file__).resolve().parent.parent / "music_theory" / "resources" / "icons"


def main() -> None:
    source = ICONS / "conservatory.svg"
    renderer = QSvgRenderer(str(source))
    if not renderer.isValid():
        raise RuntimeError(f"Cannot render {source}")
    raster = QImage(256, 256, QImage.Format.Format_ARGB32)
    raster.fill(Qt.GlobalColor.transparent)
    painter = QPainter(raster)
    renderer.render(painter)
    painter.end()
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    raster.save(buffer, "PNG")
    icon = Image.open(BytesIO(bytes(buffer.data())))
    target = ICONS / "icon.ico"
    icon.save(target, format="ICO", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    print(f"wrote {target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
