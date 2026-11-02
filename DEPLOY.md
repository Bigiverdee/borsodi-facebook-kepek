# Borsodi Facebook képösszeillesztő

Külön Render Python web service, nem módosítja a Jarvist.

## Endpoint
- GET /health (az original_overlay_installed érték mutatja, hogy a pontos PNG telepítve van-e)
- POST /compose, x-api-key header, JSON body: {"image_base64":"..."}
- Kimenet: image/png, 1080 × 1350

## Render
Build command: pip install -r requirements.txt
Start command: uvicorn app:app --host 0.0.0.0 --port $PORT
Environment: IMAGE_API_KEY = hosszú titkos érték.

## Eredeti arculati PNG
Töltsd fel a korábban elkészült **overlay.png** állományt a repó gyökerébe.
Addig az alkalmazás tartalmaz egy egyszerű, ideiglenes céges sávot.
A végleges PNG feltöltése automatikusan új telepítést indít.

## Make
OpenAI Generate Images -> HTTP Make a Request POST /compose.
Content-Type: application/json
x-api-key: a Render környezeti kulcs.
JSON body: {"image_base64":"<base64 encoded OpenAI image binary>"}
A HTTP válasz PNG-bináris adatát mapeld a Facebook Pages photo Data mezőjébe.

Ne kapcsold be az automatikus Facebook-publikálást a tesztig.
