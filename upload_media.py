"""
Pre-sube los 3 archivos estáticos (2 certificados + audio) a Meta una vez.
Guarda los media_id en media_cache.json (válidos 30 días).
Ejecutar: python3 upload_media.py
Re-ejecutar cada ~25 días para renovar los ids.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import wa_api, config

def upload_all():
    cache = {}

    print("Subiendo certificado MD Tıp Doktoru...")
    cache["cert_1_id"] = wa_api.upload_media(config.CERT_1_PATH, "application/pdf")
    print(f"  ✅ cert_1_id: {cache['cert_1_id']}")

    print("Subiendo certificado Medicina Estética...")
    cache["cert_2_id"] = wa_api.upload_media(config.CERT_2_PATH, "application/pdf")
    print(f"  ✅ cert_2_id: {cache['cert_2_id']}")

    print("Subiendo vídeo de la clínica...")
    cache["video_id"] = wa_api.upload_media(config.VIDEO_PATH, "video/mp4")
    print(f"  ✅ video_id: {cache['video_id']}")

    print("Subiendo audio de bienvenida...")
    cache["audio_id"] = wa_api.upload_media(config.AUDIO_PATH, "audio/mp4")
    print(f"  ✅ audio_id: {cache['audio_id']}")

    from datetime import datetime
    cache["uploaded_at"] = datetime.now().isoformat()
    cache["expires_note"] = "Meta media_id válidos ~30 días. Re-subir antes de que expiren."

    json.dump(cache, open(config.MEDIA_CACHE, "w"), indent=2)
    print(f"\n✅ media_cache.json guardado en {config.MEDIA_CACHE}")
    return cache

if __name__ == "__main__":
    upload_all()
