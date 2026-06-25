import requests, config

BASE = f"https://graph.facebook.com/v22.0/{config.PHONE_ID}"
HEADERS = lambda: {"Authorization": f"Bearer {config.WA_TOKEN}", "Content-Type": "application/json"}

def send_text(to, body):
    r = requests.post(f"{BASE}/messages", headers=HEADERS(), json={
        "messaging_product": "whatsapp", "to": to,
        "type": "text", "text": {"body": body}
    })
    return r.json()

def send_document(to, media_id, filename, caption=""):
    r = requests.post(f"{BASE}/messages", headers=HEADERS(), json={
        "messaging_product": "whatsapp", "to": to,
        "type": "document",
        "document": {"id": media_id, "filename": filename, "caption": caption}
    })
    return r.json()

def send_video(to, media_id, caption=""):
    r = requests.post(f"{BASE}/messages", headers=HEADERS(), json={
        "messaging_product": "whatsapp", "to": to,
        "type": "video", "video": {"id": media_id, "caption": caption}
    })
    return r.json()

def send_audio(to, media_id):
    r = requests.post(f"{BASE}/messages", headers=HEADERS(), json={
        "messaging_product": "whatsapp", "to": to,
        "type": "audio", "audio": {"id": media_id}
    })
    return r.json()

def forward_image(to, media_id, caption=""):
    r = requests.post(f"{BASE}/messages", headers=HEADERS(), json={
        "messaging_product": "whatsapp", "to": to,
        "type": "image", "image": {"id": media_id, "caption": caption}
    })
    return r.json()

def upload_media(file_path, mime_type):
    headers = {"Authorization": f"Bearer {config.WA_TOKEN}"}
    with open(file_path, "rb") as f:
        r = requests.post(
            f"https://graph.facebook.com/v22.0/{config.PHONE_ID}/media",
            headers=headers,
            files={"file": (file_path.split("/")[-1], f, mime_type)},
            data={"messaging_product": "whatsapp", "type": mime_type}
        )
    result = r.json()
    if "id" not in result:
        raise Exception(f"Upload failed: {result}")
    return result["id"]
