"""Convert the approved PNG artwork to the icon formats used by Briefcase."""
from pathlib import Path

from PIL import Image


ICON_DIRECTORY = Path(__file__).resolve().parents[1] / "resources" / "icon"
PNG_SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)


def prepare_icons():
    with Image.open(ICON_DIRECTORY / "icon-source.png") as source:
        image = source.convert("RGBA")
    if image.width != image.height:
        raise ValueError("Application icon artwork must be square")

    master = image.resize((1024, 1024), Image.Resampling.LANCZOS)
    master.save(ICON_DIRECTORY / "icon.png")
    for size in PNG_SIZES:
        master.resize((size, size), Image.Resampling.LANCZOS).save(
            ICON_DIRECTORY / f"icon-{size}.png"
        )
    master.save(ICON_DIRECTORY / "icon.ico", format="ICO",
                sizes=[(size, size) for size in PNG_SIZES if size <= 256])
    master.save(ICON_DIRECTORY / "icon.icns", format="ICNS")


if __name__ == "__main__":
    prepare_icons()
