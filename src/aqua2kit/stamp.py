"""Burn per-frame timestamps into a multi-page TIFF stack."""
from pathlib import Path

_FONT_PATH = "/usr/share/fonts/liberation-mono/LiberationMono-Regular.ttf"


def stamp_tiff(src: str, fps: float, dst: str | None = None,
               font_size: int = 14, color: str = "white",
               bg_color: str = "black", bg_opacity: float = 0.55,
               margin: int = 6) -> str:
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np

    src = Path(src)
    dst = Path(dst) if dst else src.with_stem(src.stem + "_stamped")

    try:
        font = ImageFont.truetype(_FONT_PATH, font_size)
    except OSError:
        font = ImageFont.load_default(size=font_size)

    frames = []
    with Image.open(src) as im:
        for i in range(im.n_frames):
            im.seek(i)
            frame = im.convert("RGB").copy()
            t_sec = i / fps
            label = f"t = {t_sec:6.1f} s"

            draw = ImageDraw.Draw(frame, "RGBA")
            bbox = draw.textbbox((margin, margin), label, font=font)
            pad = 3
            box = (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad)
            alpha = int(bg_opacity * 255)
            draw.rectangle(box, fill=(*Image.new("RGB", (1, 1), bg_color).getpixel((0, 0)), alpha))
            draw = ImageDraw.Draw(frame)
            draw.text((margin, margin), label, font=font, fill=color)

            frames.append(frame)

    frames[0].save(dst, save_all=True, append_images=frames[1:], compression="tiff_lzw")
    return str(dst)
