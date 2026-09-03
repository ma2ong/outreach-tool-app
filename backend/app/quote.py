"""Product quote card: render selected products into a shareable PNG.

Customers ask for specs+price constantly; instead of retyping, the rep picks
products and gets a branded card image whose file path drops straight into the
existing send attachment slot (email attachment / WA·IG image). Rendered with
PIL — no browser, no new deps.
"""
import datetime as _dt
import os

from PIL import Image, ImageDraw, ImageFont

# Allen's standard range — loaded via the seed endpoint, then editable in the UI.
DEFAULT_PRODUCTS = [
    {"model": "Indoor Fine Pitch", "pixel_pitch": "P0.6-P1.8", "brightness": "600-800 nits",
     "use_case": "Control room / TV studio / boardroom", "ref_price_sqm": "USD 2400-5800"},
    {"model": "Indoor Commercial", "pixel_pitch": "P2-P4", "brightness": "600-800 nits",
     "use_case": "Retail / conference / stage backdrop", "ref_price_sqm": "USD 900-1800"},
    {"model": "Indoor Rental", "pixel_pitch": "P2.6-P3.9", "brightness": "600-800 nits",
     "use_case": "Events / concerts (die-cast cabinet)", "ref_price_sqm": "USD 1000-1600"},
    {"model": "Outdoor Rental", "pixel_pitch": "P3.9-P4.8", "brightness": "4500-5500 nits",
     "use_case": "Outdoor stages / festivals", "ref_price_sqm": "USD 1100-1700"},
    {"model": "Outdoor Fixed", "pixel_pitch": "P2.5-P10", "brightness": "5500-8000 nits",
     "use_case": "Billboards / building facade", "ref_price_sqm": "USD 500-1100"},
]

from app import identity

_BRAND = identity.COMPANY
_CONTACT = identity.CONTACT_LINE
_COLS = [("Model", 240), ("Pixel pitch", 150), ("Brightness", 170),
         ("Application", 330), ("Ref. price / m²", 190)]
_KEYS = ["model", "pixel_pitch", "brightness", "use_case", "ref_price_sqm"]


def _font(size: int, bold: bool = False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", name), size)
    except Exception:  # noqa: BLE001 - non-Windows fallback
        return ImageFont.load_default()


def render_quote(products: list[dict], out_path: str, note: str = "") -> str:
    width = 40 + sum(w for _, w in _COLS) + 40
    row_h, header_h, top = 56, 46, 150
    note_h = 40 if note else 0
    height = top + header_h + row_h * len(products) + note_h + 110
    img = Image.new("RGB", (width, height), "#ffffff")
    d = ImageDraw.Draw(img)

    # header band
    d.rectangle([0, 0, width, 96], fill="#0f2a43")
    d.text((40, 22), _BRAND, font=_font(30, True), fill="#ffffff")
    d.text((40, 62), "LED Display Reference Price Sheet", font=_font(20), fill="#9fc3e8")
    d.text((width - 40, 62), _dt.date.today().isoformat(), font=_font(18), fill="#9fc3e8", anchor="ra")

    # table header
    x, y = 40, top
    d.rectangle([40, y, width - 40, y + header_h], fill="#e8eef5")
    for name, w in _COLS:
        d.text((x + 12, y + 12), name, font=_font(19, True), fill="#0f2a43")
        x += w
    y += header_h
    # rows
    for i, p in enumerate(products):
        if i % 2:
            d.rectangle([40, y, width - 40, y + row_h], fill="#f6f9fc")
        x = 40
        for (name, w), key in zip(_COLS, _KEYS):
            d.text((x + 12, y + 16), str(p.get(key) or "-"), font=_font(18), fill="#22313f")
            x += w
        y += row_h
    d.rectangle([40, top, width - 40, y], outline="#c9d6e2", width=1)

    if note:
        d.text((40, y + 12), f"Note: {note}", font=_font(17), fill="#5b6b7a")
        y += note_h

    d.text((40, y + 26), "Prices are FOB Shenzhen reference, vary with spec/quantity. Valid 30 days.",
           font=_font(16), fill="#8a97a3")
    d.text((40, y + 54), _CONTACT, font=_font(17, True), fill="#0f2a43")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    img.save(out_path, "PNG")
    return out_path
