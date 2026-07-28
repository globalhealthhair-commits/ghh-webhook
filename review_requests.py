"""
Solicitud automatica de reseñas (Google + Trustpilot) a pacientes de Dr. Merdan Celik.
Se ejecuta diariamente: busca en la hoja de Drive quien tuvo check-in hace 1 dia,
y envia email de solicitud de reseña (unico enlace /valoranos/, sin gating ni incentivo).

WhatsApp: pendiente activar cuando se desbloquee el acceso a la API de Meta
(ver memoria: "API access blocked" detectado 28-jul-2026). El codigo de envio WA
esta preparado (send_review_whatsapp) pero deshabilitado hasta entonces.
"""
import json
import os
import re
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE = os.path.dirname(os.path.abspath(__file__))
GOOGLE_TOKENS_PATH = os.path.join(BASE, "..", "credentials", "google_tokens.json")
SENT_LOG_PATH = os.path.join(BASE, "data", "review_requests_sent.json")

SHEET_ID = "1uMECTEaF8DzdpcxnFKTcGELK4GgRrpfeHFr3xbLRFkY"  # "Tabla Merdan Celik" 2026

# Atribucion de mercado: columna "Country" (pais de origen/salida) manda SIEMPRE.
# El nombre/apellido NUNCA decide por si solo -- solo se usa como señal secundaria
# si el pais viene vacio/ambiguo. Evita el error de asumir mercado por apellido
# de sonido español cuando el pais real es otro (ej. Lauria/Fierro con pais
# Paises Bajos/Mexico -- NO son mercado España pese al apellido).
SPAIN_COUNTRIES = {"spain", "espana", "españa"}


def _is_spain_market(country_raw, city_raw=""):
    country = (country_raw or "").strip().lower()
    if country in SPAIN_COUNTRIES:
        return True
    if country:
        return False  # pais explicito y no es España -> NO es mercado España, sin excepcion
    # Pais vacio/ambiguo: fallback muy conservador a ciudad de residencia
    city = (city_raw or "").strip().lower()
    spain_cities_hint = {"madrid", "barcelona", "sevilla", "valencia", "bilbao",
                          "las palmas", "tenerife", "malaga", "granada", "santander"}
    return city in spain_cities_hint

SMTP_HOST = "smtp.hostinger.com"
SMTP_PORT = 465
SMTP_USER = "info@trasplantepeloturquia.com"
BCC = "sergimaymo@gmail.com"


def _sheets_service():
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if refresh_token and client_id and client_secret:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
    else:
        with open(GOOGLE_TOKENS_PATH) as f:
            tok = json.load(f)
        creds = Credentials(
            token=tok.get("access_token"),
            refresh_token=tok.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=tok.get("client_id"),
            client_secret=tok.get("client_secret"),
            scopes=tok.get("scope", "").split(),
        )
    return build("sheets", "v4", credentials=creds)


def _load_sent_log():
    if os.path.exists(SENT_LOG_PATH):
        return json.load(open(SENT_LOG_PATH))
    return {}


def _save_sent_log(data):
    os.makedirs(os.path.dirname(SENT_LOG_PATH), exist_ok=True)
    json.dump(data, open(SENT_LOG_PATH, "w"), indent=2, ensure_ascii=False)


def _parse_date(s):
    for fmt in ("%d/%m/%Y",):
        try:
            return datetime.strptime(s.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _extract_first_name(raw_name):
    name = re.sub(r"\(.*?\)", "", raw_name).strip()
    return name.split()[0] if name else "amigo/a"


def _extract_email(raw):
    if not raw:
        return None
    raw = raw.strip()
    if "@" in raw and "." in raw:
        return raw
    return None


def _send_email(name_first, email):
    subject = "Tu opinion nos ayuda mucho - Global Health Hair"
    body = f"""Hola {name_first},

Esperamos que estes disfrutando de los resultados de tu trasplante capilar con el Dr. Merdan Celik.

Tu opinion es muy valiosa para nosotros y para otros pacientes que estan valorando dar el paso. Si tienes un minuto, nos ayudaria mucho que compartieras tu experiencia:

https://trasplantepeloturquia.com/valoranos/

Ahi encontraras el enlace directo a Google y a Trustpilot, y tambien la opcion de escribirnos directamente si lo prefieres.

Muchas gracias por confiar en nosotros.

Un cordial saludo,
Dr. Merdan Celik / Global Health Hair Istanbul
trasplantepeloturquia.com | info@trasplantepeloturquia.com
"""
    smtp_pass = os.environ.get("HOSTINGER_SMTP_PASS")
    if not smtp_pass:
        creds_path = os.path.join(BASE, "..", "credentials", "smtp_credentials.txt")
        if os.path.exists(creds_path):
            for line in open(creds_path):
                if line.startswith("SMTP_PASS="):
                    smtp_pass = line.strip().split("=", 1)[1]
    if not smtp_pass:
        raise RuntimeError("Falta HOSTINGER_SMTP_PASS (variable de entorno en Railway)")

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = email
    msg["Bcc"] = BCC
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SMTP_USER, smtp_pass)
        server.sendmail(SMTP_USER, [email, BCC], msg.as_string())


def run_review_requests():
    """Job diario: busca pacientes con check-in = ayer, envia solicitud de reseña una sola vez por email."""
    print("[REVIEW_REQ] Ejecutando chequeo diario de solicitudes de reseña...")
    service = _sheets_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range="A1:AF200"
    ).execute()
    rows = result.get("values", [])

    yesterday = (datetime.now() - timedelta(days=1)).date()
    sent_log = _load_sent_log()
    sent_count = 0

    for row in rows:
        if len(row) < 28:
            continue
        raw_name = row[1] if len(row) > 1 else ""
        residencial_city = row[4] if len(row) > 4 else ""
        country_raw = row[6] if len(row) > 6 else ""  # columna "Country" (origen)
        checkin_raw = row[11] if len(row) > 11 else ""  # columna "Check-in"
        phone = row[26] if len(row) > 26 else ""
        email = _extract_email(row[27] if len(row) > 27 else "")  # columna "e-mail"

        checkin = _parse_date(checkin_raw)
        if not checkin or checkin.date() != yesterday:
            continue
        if not email:
            continue
        if not _is_spain_market(country_raw, residencial_city):
            print(f"[REVIEW_REQ] SKIP (no es mercado España, pais={country_raw!r}): {raw_name}")
            continue

        key = f"{raw_name.strip()}|{email.lower()}"
        if key in sent_log:
            continue

        first_name = _extract_first_name(raw_name)
        try:
            _send_email(first_name, email)
            sent_log[key] = datetime.now().isoformat()
            sent_count += 1
            print(f"[REVIEW_REQ] Email enviado a {raw_name} <{email}>")
        except Exception as e:
            print(f"[REVIEW_REQ] ERROR enviando a {raw_name} <{email}>: {e}")

    _save_sent_log(sent_log)
    print(f"[REVIEW_REQ] Completado. {sent_count} solicitud(es) de reseña enviada(s) hoy.")


# WhatsApp — preparado, deshabilitado hasta que se desbloquee el acceso a la API de Meta
def send_review_whatsapp(phone, first_name, lang="es"):
    """Placeholder: activar cuando la API de Meta deje de devolver 'API access blocked'."""
    raise NotImplementedError("WhatsApp API bloqueada (ver memoria 28-jul-2026) — usar solo email por ahora")


if __name__ == "__main__":
    run_review_requests()
