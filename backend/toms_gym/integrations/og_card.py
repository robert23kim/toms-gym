"""OG (Open Graph) share-card image generation for T13.

Pure Pillow-only renderer plus the server-side meta HTML for crawler unfurls.
Everything here is DB-free and network-free so it can be unit tested without a
database or GCS. `render_card_png` returns PNG bytes for a 1200x630 social card
(title, big stat/grade, description, brand footer) tinted by sport `kind`
(lift|bowling|golf). `render_meta_html` returns the HTML a crawler receives.
"""

import html
import io
import json

from PIL import Image, ImageDraw, ImageFont

CARD_W, CARD_H = 1200, 630

# sport -> (background RGB, accent RGB)
_KIND_THEME = {
    "lift": ((15, 23, 42), (96, 165, 250)),      # slate / blue
    "bowling": ((23, 16, 43), (167, 139, 250)),  # indigo / violet
    "golf": ((6, 46, 33), (52, 211, 153)),       # deep green / emerald
    "default": ((15, 23, 42), (148, 163, 184)),
}

_KIND_LABEL = {
    "lift": "LIFT ANALYSIS",
    "bowling": "BOWLING ANALYSIS",
    "golf": "GOLF ROUND",
    "default": "TOM'S GYM",
}


def infer_kind(target_url: str) -> str:
    """Best-effort sport classification from a result URL path."""
    u = (target_url or "").lower()
    if "/bowling/" in u:
        return "bowling"
    if "/golf/" in u:
        return "golf"
    if "/video/" in u or "/lift" in u or "/challenges/" in u:
        return "lift"
    return "default"


def _font(size: int, bold: bool = False):
    """Load a scalable font, preferring bundled/system TrueType, else default."""
    candidates = [
        f"DejaVuSans{'-Bold' if bold else ''}.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else ""),
        "Arial Bold.ttf" if bold else "Arial.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10 scalable default
    except TypeError:
        return ImageFont.load_default()


def _text_w(draw, text, font) -> int:
    return int(draw.textlength(text, font=font))


def _wrap(draw, text, font, max_w):
    """Greedy word-wrap; returns a list of lines that each fit in max_w."""
    words = (text or "").split()
    if not words:
        return [""]
    lines, cur = [], words[0]
    for w in words[1:]:
        trial = cur + " " + w
        if _text_w(draw, trial, font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def render_card_png(kind: str, title: str, stat: str = "", description: str = "") -> bytes:
    """Render a 1200x630 share card as PNG bytes. Pure — no DB, no network."""
    kind = kind if kind in _KIND_THEME else "default"
    bg, accent = _KIND_THEME[kind]

    img = Image.new("RGB", (CARD_W, CARD_H), bg)
    draw = ImageDraw.Draw(img)

    # Accent side-bar for a branded frame.
    draw.rectangle([0, 0, 16, CARD_H], fill=accent)

    pad = 72
    max_w = CARD_W - pad * 2

    # Kicker / sport label.
    label = _KIND_LABEL.get(kind, _KIND_LABEL["default"])
    label_font = _font(30, bold=True)
    draw.text((pad, 64), label, font=label_font, fill=accent)

    # Big stat / grade — the punch of the card.
    stat = (stat or "").strip()
    if stat:
        stat_font = _font(190, bold=True)
        # Shrink to fit if the stat is long (e.g. "Straight").
        while _text_w(draw, stat, stat_font) > max_w and stat_font.size > 60:
            stat_font = _font(stat_font.size - 12, bold=True)
        draw.text((pad, 120), stat, font=stat_font, fill=(255, 255, 255))
        title_y = 120 + stat_font.size + 24
    else:
        title_y = 150

    # Title (wrapped).
    title_font = _font(58, bold=True)
    for line in _wrap(draw, title, title_font, max_w)[:2]:
        draw.text((pad, title_y), line, font=title_font, fill=(226, 232, 240))
        title_y += title_font.size + 10

    # Description (wrapped, muted).
    if description:
        desc_font = _font(38)
        dy = title_y + 8
        for line in _wrap(draw, description, desc_font, max_w)[:2]:
            draw.text((pad, dy), line, font=desc_font, fill=(148, 163, 184))
            dy += desc_font.size + 8

    # Brand footer.
    brand_font = _font(34, bold=True)
    draw.text((pad, CARD_H - 70), "Tom's Gym", font=brand_font, fill=accent)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_meta_html(title: str, description: str, image_url: str, target_url: str, kind: str = "default") -> str:
    """Server-rendered HTML with OG/Twitter tags for crawler unfurls.

    Humans who land here (JS enabled) are bounced to `target_url` immediately;
    crawlers read the meta tags. Kept pure so it is unit-testable.
    """
    t = html.escape(title or "Tom's Gym")
    d = html.escape(description or "See the analysis on Tom's Gym.")
    tgt = html.escape(target_url or "/", quote=True)
    tags = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{t}</title>",
        f'<meta property="og:title" content="{t}">',
        f'<meta property="og:description" content="{d}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:url" content="{tgt}">',
        '<meta property="og:site_name" content="Tom\'s Gym">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{t}">',
        f'<meta name="twitter:description" content="{d}">',
    ]
    if image_url:
        iu = html.escape(image_url, quote=True)
        tags.append(f'<meta property="og:image" content="{iu}">')
        tags.append('<meta property="og:image:width" content="1200">')
        tags.append('<meta property="og:image:height" content="630">')
        tags.append(f'<meta name="twitter:image" content="{iu}">')

    head = "\n    ".join(tags)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n  <head>\n    '
        f"{head}\n"
        f'    <meta http-equiv="refresh" content="0; url={tgt}">\n'
        "  </head>\n  <body>\n"
        f'    <p>Redirecting to <a href="{tgt}">your result</a>…</p>\n'
        f"    <script>window.location.replace({json.dumps(target_url or '/')});</script>\n"
        "  </body>\n</html>\n"
    )
