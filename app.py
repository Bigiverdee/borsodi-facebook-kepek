import base64
import binascii
import io
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, File, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pydantic import BaseModel

app = FastAPI(title="Borsodi Facebook image composer")
WIDTH, HEIGHT, FOOTER_TOP = 1080, 1350, 1065
API_KEY = os.environ.get("IMAGE_API_KEY", "")
OVERLAY_FILE = Path(__file__).with_name("overlay.png")

class ComposeRequest(BaseModel):
    image_base64: str

def brand_fallback():
    """Temporary footer until original overlay.png is uploaded."""
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, FOOTER_TOP, WIDTH, HEIGHT), fill="#ffffff")
    d.rectangle((0, FOOTER_TOP, WIDTH, FOOTER_TOP + 7), fill="#e3ac3e")
    d.polygon([(790, 1350), (1080, 1160), (1080, 1350)], fill="#2563eb")
    d.polygon([(925, 1350), (1080, 1250), (1080, 1350)], fill="#113c91")
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(bold_path, 42)
    small = ImageFont.truetype(font_path, 28)
    d.rectangle((38, FOOTER_TOP+52, 98, FOOTER_TOP+113), outline="#2563eb", width=6)
    d.line((68, FOOTER_TOP+52, 68, FOOTER_TOP+113), fill="#2563eb", width=5)
    d.text((123, FOOTER_TOP+57), "Borsodi Nyílászáró Szakik", font=font, fill="#142d52")
    d.text((45, FOOTER_TOP+170), "borsodinyilaszaro.hu", font=small, fill="#142d52")
    d.text((455, FOOTER_TOP+170), "+36 20 269 0396", font=small, fill="#142d52")
    return canvas

def get_overlay():
    if OVERLAY_FILE.exists():
        with Image.open(OVERLAY_FILE) as image:
            return image.convert("RGBA").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    return brand_fallback()

@app.get("/health")
def health():
    return {"ok": True, "original_overlay_installed": OVERLAY_FILE.exists()}

@app.post("/compose")
def compose(body: ComposeRequest, x_api_key: str | None = Header(default=None)):
    import hmac
    if not API_KEY or not x_api_key or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized")
    payload = body.image_base64.split(",", 1)[-1]
    if len(payload) > 18_000_000:
        raise HTTPException(status_code=413, detail="Image too large")
    try:
        raw = base64.b64decode(payload, validate=True)
        Image.MAX_IMAGE_PIXELS = 22_000_000
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            photo = ImageOps.fit(image.convert("RGB"), (WIDTH, FOOTER_TOP),
                                method=Image.Resampling.LANCZOS)
    except (ValueError, binascii.Error, OSError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail="Invalid image input")
    result = Image.new("RGBA", (WIDTH, HEIGHT), "#ffffff")
    result.paste(photo, (0, 0))
    result.alpha_composite(get_overlay())
    out = io.BytesIO()
    result.convert("RGB").save(out, format="PNG", optimize=True)
    return Response(content=out.getvalue(), media_type="image/png")


@app.post("/compose-file")
async def compose_file(image: UploadFile = File(...), x_api_key: str | None = Header(default=None)):
    import hmac
    if not API_KEY or not x_api_key or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized")
    raw = await image.read(12_000_001)
    if len(raw) > 12_000_000:
        raise HTTPException(status_code=413, detail="Image too large")
    return compose(ComposeRequest(image_base64=base64.b64encode(raw).decode("ascii")), x_api_key)
