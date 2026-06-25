"""
Notificaciones al admin via Telegram bot @ghh_admin_bot.
Sin restricciones de ventana 24h, fotos en álbum agrupado.
"""
import json, os, requests
import config

TOKEN   = config.TG_TOKEN
CHAT_ID = config.TG_CHAT_ID
API     = f"https://api.telegram.org/bot{TOKEN}"


def send_text(text: str):
    requests.post(f"{API}/sendMessage", json={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    })


def send_photo(file_bytes: bytes, caption: str = ""):
    requests.post(f"{API}/sendPhoto", data={"chat_id": CHAT_ID, "caption": caption},
                  files={"photo": ("foto.jpg", file_bytes, "image/jpeg")})


def send_photo_album(photos: list[bytes], caption: str = ""):
    """Envía varias fotos como álbum agrupado (máximo 10)."""
    if not photos:
        return
    media = []
    files = {}
    for i, b in enumerate(photos[:10]):
        key = f"photo{i}"
        files[key] = (f"foto{i}.jpg", b, "image/jpeg")
        media.append({"type": "photo", "media": f"attach://{key}",
                      **({"caption": caption} if i == 0 else {})})
    requests.post(f"{API}/sendMediaGroup",
                  data={"chat_id": CHAT_ID, "media": json.dumps(media)},
                  files=files)


def send_document(file_bytes: bytes, filename: str, caption: str = ""):
    requests.post(f"{API}/sendDocument",
                  data={"chat_id": CHAT_ID, "caption": caption},
                  files={"document": (filename, file_bytes, "application/pdf")})
