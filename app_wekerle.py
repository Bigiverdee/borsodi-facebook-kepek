import io
import os
import hmac
from fastapi import FastAPI, File, UploadFile, Form, Header, HTTPException
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFont, ImageOps

app = FastAPI(title="Wekerle Borsod Facebook Image Composer")
WIDTH, HEIGHT = 1080, 1350
API_KEY = os.environ.get("IMAGE_API_KEY", "")
THEMES = {
    "blue_gold": ("#102E5D", "#E6BA61"),
    "blue_white": ("#164B8B", "#C5E7FF"),
    "green_terracotta": ("#234A3C", "#ECB096"),
    "purple_cream": ("#45335F", "#F2D5A2"),
    "sage_green": ("#3C5E50", "#D4E6BE"),
}
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def font(size, bold=False):
    try:
        return ImageFont.truetype(BOLD if bold else REGULAR, size)
    except OSError:
        return ImageFont.load_default()

def fit_lines(draw, raw, max_width=960, max_lines=2, start=78, minimum=37):
    words = " ".join((raw or "").split())[:140].split()
    for sz in range(start, minimum - 1, -2):
        face = font(sz, True)
        lines, current = [], ""
        for word in words:
            candidate = (current + " " + word).strip()
            if draw.textbbox((0, 0), candidate, font=face)[2] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        if len(lines) <= max_lines and all(draw.textbbox((0, 0), l, font=face)[2] <= max_width for l in lines):
            return lines, face, sz
    return ["WEKERLE+ FELÚJÍTÁS"], font(60, True), 60

def fit_single(draw, raw, max_width, start=38, minimum=24):
    words = " ".join((raw or "").split())[:170]
    for sz in range(start, minimum-1, -2):
        face = font(sz)
        if draw.textbbox((0, 0), words, font=face)[2] <= max_width:
            return words, face
    face = font(minimum)
    while words and draw.textbbox((0, 0), words + "…", font=face)[2] > max_width:
        words = words[:-1].rstrip()
    return words + "…", face

def compose_image(raw, headline, subheadline, theme):
    bg, accent = THEMES[theme]
    with Image.open(io.BytesIO(raw)) as original:
        original.load()
        photo = ImageOps.fit(ImageOps.exif_transpose(original).convert("RGB"), (WIDTH, HEIGHT),
                             method=Image.Resampling.LANCZOS, centering=(0.5, 0.47))
    out = photo.convert("RGBA")
    # Transparent gradient rather than an opaque lower panel.
    gradient = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pixels = gradient.load()
    rgb = tuple(bytes.fromhex(bg.lstrip("#")))
    for y in range(610, HEIGHT):
        t = (y - 610) / (HEIGHT - 610)
        alpha = int(220 * (t ** 0.75))
        for x in range(WIDTH):
            pixels[x, y] = (*rgb, alpha)
    out = Image.alpha_composite(out, gradient)
    d = ImageDraw.Draw(out)
    # Distinct but compact floating campaign badge.
    d.rounded_rectangle((48, 52, 426, 124), radius=19, fill=bg)
    d.rounded_rectangle((48, 52, 57, 124), radius=4, fill=accent)
    d.text((79, 70), "WEKERLE+  |  BORSOD", font=font(30, True), fill="#FFFFFF")
    lines, headline_font, sz = fit_lines(d, headline)
    top = 955 if len(lines) == 1 else 880
    for line in lines:
        d.text((49, top), line, font=headline_font, fill="#FFFFFF",
               stroke_width=2, stroke_fill=(0, 0, 0, 85))
        top += sz + 19
    subtitle, sub_font = fit_single(d, subheadline, 975)
    d.text((51, top + 10), subtitle, font=sub_font, fill="#FFFFFF")
    d.rounded_rectangle((48, 1192, 622, 1272), radius=16, fill=accent)
    d.text((70, 1215), "JELENTKEZÉS  •  wekerleborsod.hu", font=font(26, True), fill=bg)
    d.text((50, 1304), "FLO INVEST Kft.  |  Nem hivatalos pályázati oldal", font=font(20),
           fill="#FFFFFF")
    return out.convert("RGB")

@app.get("/health")
def health():
    return {"ok": True, "service": "wekerle-facebook-kepek", "design": "full_bleed_v2", "themes": list(THEMES)}

@app.post("/compose-file")
async def compose_file(
    image: UploadFile = File(...),
    headline: str = Form("Korszerűbb otthon Borsodban"),
    subheadline: str = Form("Előzetes érdeklődés a felújítási lehetőségekről"),
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
        result = compose_image(raw, headline, subheadline, theme)
    except (OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail="Invalid image")
    buf = io.BytesIO()
    result.save(buf, format="PNG", optimize=True)
    return Response(content=buf.getvalue(), media_type="image/png")
