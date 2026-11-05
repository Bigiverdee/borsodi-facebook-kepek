import io
import os
import hmac
from fastapi import FastAPI, File, UploadFile, Form, Header, HTTPException
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFont, ImageOps

app = FastAPI(title="Wekerle Borsod Facebook Image Composer")
WIDTH, HEIGHT = 1080, 1350
IMAGE_HEIGHT = 1000
API_KEY = os.environ.get("IMAGE_API_KEY", "")
THEMES = {
    "blue_gold": ("#102E5D", "#E6BA61", "#FFFFFF"),
    "blue_white": ("#164B8B", "#D9EBFA", "#FFFFFF"),
    "green_terracotta": ("#234A3C", "#D18B69", "#FFFFFF"),
    "purple_cream": ("#45335F", "#E9D6B1", "#FFFFFF"),
    "sage_green": ("#3C5E50", "#BBD3B6", "#FFFFFF"),
}
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def font(size, bold=False):
    path = BOLD if bold else REGULAR
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()

def fit_text(draw, value, max_width, preferred, minimum=24, bold=False):
    text = " ".join((value or "").split())[:180]
    for size in range(preferred, minimum - 1, -2):
        f = font(size, bold)
        if draw.textbbox((0, 0), text, font=f)[2] <= max_width:
            return text, f
    words = text.split()
    while words and draw.textbbox((0, 0), " ".join(words) + "…", font=font(minimum, bold))[2] > max_width:
        words.pop()
    return " ".join(words) + ("…" if words else ""), font(minimum, bold)

@app.get("/health")
def health():
    return {"ok": True, "service": "wekerle-facebook-kepek", "themes": list(THEMES)}

@app.post("/compose-file")
async def compose_file(
    image: UploadFile = File(...),
    headline: str = Form("WEKERLE+ FELÚJÍTÁS"),
    subheadline: str = Form("Érdeklődjön a lehetőségekről Borsodban!"),
    theme: str = Form("blue_gold"),
    x_api_key: str | None = Header(default=None),
):
    if not API_KEY or not x_api_key or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if theme not in THEMES:
        raise HTTPException(status_code=400, detail="Unknown theme")
    raw = await image.read(12_000_001)
    if len(raw) > 12_000_000:
        raise HTTPException(status_code=413, detail="Image too large")
    try:
        Image.MAX_IMAGE_PIXELS = 22_000_000
        with Image.open(io.BytesIO(raw)) as original:
            original.load()
            photo = ImageOps.fit(ImageOps.exif_transpose(original).convert("RGB"), (WIDTH, IMAGE_HEIGHT), method=Image.Resampling.LANCZOS)
    except (OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail="Invalid image")

    bg, accent, white = THEMES[theme]
    out = Image.new("RGB", (WIDTH, HEIGHT), bg)
    out.paste(photo, (0, 0))
    d = ImageDraw.Draw(out)
    d.rectangle((0, IMAGE_HEIGHT, WIDTH, IMAGE_HEIGHT + 12), fill=accent)
    d.rectangle((0, IMAGE_HEIGHT + 12, 16, HEIGHT), fill=accent)
    d.rounded_rectangle((48, IMAGE_HEIGHT + 34, 340, IMAGE_HEIGHT + 84), radius=18, fill=accent)
    d.text((66, IMAGE_HEIGHT + 43), "WEKERLE+  •  BORSOD", fill=bg, font=font(23, True))
    title, title_font = fit_text(d, headline, 970, 61, 28, True)
    d.text((48, IMAGE_HEIGHT + 103), title, fill=white, font=title_font)
    subtitle, sub_font = fit_text(d, subheadline, 970, 33, 22, False)
    d.text((50, IMAGE_HEIGHT + 195), subtitle, fill=white, font=sub_font)
    d.line((50, HEIGHT - 71, WIDTH - 50, HEIGHT - 71), fill=accent, width=2)
    d.text((50, HEIGHT - 57), "wekerleborsod.hu", fill=accent, font=font(33, True))
    d.text((WIDTH - 355, HEIGHT - 51), "FLO INVEST Kft.", fill=white, font=font(23, False))

    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return Response(content=buf.getvalue(), media_type="image/png")
