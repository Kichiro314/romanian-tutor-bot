import random
import textwrap
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# DejaVu fonts installed via apt-get fonts-dejavu-core
_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

_BG_COLORS = [
    "#E74C3C",  # red
    "#E67E22",  # orange
    "#2ECC71",  # green
    "#3498DB",  # blue
    "#9B59B6",  # purple
    "#1ABC9C",  # teal
    "#E91E63",  # pink
    "#00BCD4",  # cyan
]

W, H = 640, 400


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _auto_size(text: str, max_width: int, path: str, start_size: int) -> tuple:
    """Return (font, size) that fits text within max_width."""
    size = start_size
    while size > 14:
        f = _font(path, size)
        w = f.getlength(text)
        if w <= max_width:
            return f, size
        size -= 4
    return _font(path, 14), 14


def _draw_centered_text(draw, y, text, font, fill, max_width, stroke=0, stroke_fill=(0, 0, 0)):
    w = font.getlength(text)
    x = (W - w) / 2
    draw.text((x, y), text, font=font, fill=fill,
              stroke_width=stroke, stroke_fill=stroke_fill)


def _draw_wrapped(draw, y, text, font, fill, max_width, line_gap=6):
    """Draw word-wrapped text centered, return total height used."""
    avg_char_w = font.getlength("x")
    chars_per_line = max(1, int(max_width / avg_char_w))
    lines = textwrap.wrap(text, width=chars_per_line)[:4]
    _, _, _, line_h = font.getbbox("Ay")
    for line in lines:
        w = font.getlength(line)
        x = (W - w) / 2
        draw.text((x, y), line, font=font, fill=fill)
        y += line_h + line_gap
    return y


def create_word_meme(word_ro: str, translation_ru: str, caption: str, pronunciation: str = "") -> BytesIO:
    bg_hex = random.choice(_BG_COLORS)
    r, g, b = int(bg_hex[1:3], 16), int(bg_hex[3:5], 16), int(bg_hex[5:7], 16)

    # Work in RGBA for alpha compositing
    img = Image.new("RGBA", (W, H), (r, g, b, 255))
    draw = ImageDraw.Draw(img)

    # Romanian flag stripe at top (8px)
    draw.rectangle([0, 0, W // 3, 8], fill="#002B7F")
    draw.rectangle([W // 3, 0, 2 * W // 3, 8], fill="#FCD116")
    draw.rectangle([2 * W // 3, 0, W, 8], fill="#CE1126")

    # Semi-transparent dark band at bottom for caption
    band_h = 130
    band = Image.new("RGBA", (W, band_h), (0, 0, 0, 185))
    img.alpha_composite(band, dest=(0, H - band_h))

    draw = ImageDraw.Draw(img)

    # Romanian word — large, centered
    word_font, _ = _auto_size(word_ro, W - 60, _FONT_BOLD, 80)
    word_y = 50
    _draw_centered_text(draw, word_y, word_ro, word_font, "white", W - 60, stroke=3, stroke_fill=(0, 0, 0))

    # Pronunciation (if any)
    pron_y = word_y + word_font.getbbox("Ay")[3] + 10
    if pronunciation:
        pron_font = _font(_FONT_REG, 22)
        _draw_centered_text(draw, pron_y, f"[{pronunciation}]", pron_font, (255, 255, 200), W - 60)
        pron_y += 30

    # Translation — medium
    trans_font, _ = _auto_size(f"= {translation_ru}", W - 80, _FONT_BOLD, 38)
    trans_y = pron_y + 12
    _draw_centered_text(draw, trans_y, f"= {translation_ru}", trans_font, "white", W - 80, stroke=2, stroke_fill=(0, 0, 0))

    # Caption in dark band at bottom
    cap_font = _font(_FONT_REG, 21)
    cap_y = H - band_h + 14
    _draw_wrapped(draw, cap_y, caption, cap_font, (255, 255, 200), W - 60)

    # Convert to RGB and save
    final = img.convert("RGB")
    buf = BytesIO()
    final.save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf
