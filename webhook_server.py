"""
Servidor webhook WhatsApp Business — GHH
Recibe mensajes del 638, ejecuta la secuencia automática y procesa comandos ##.

Arrancar:   python3 webhook_server.py
Exponer:    ngrok http 5000   (o Railway/Render en producción)
URL Meta:   https://TU_DOMINIO/webhook
"""
import json, os, sys, time, threading, re, csv as csv_mod
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify
import wa_api, config, scheduler
from informe_generator import generate_informe

# ── Detección de idioma ───────────────────────────────────────────
_LANG_PATTERNS = {
    "en": re.compile(r'\b(hello|hi|hey|thanks|thank you|information|please|would|could|hair|transplant|cost|price|i want|i need|i am|how much|what is|appointment)\b', re.I),
    "de": re.compile(r'\b(hallo|guten|danke|bitte|ich|haare|transplantation|kosten|preis|möchte|brauche|wie viel|was kostet|termin)\b', re.I),
    "fr": re.compile(r'\b(bonjour|salut|merci|s\'il vous plaît|je|cheveux|transplantation|coût|prix|voudrais|besoin|combien|qu\'est|rendez)\b', re.I),
    "it": re.compile(r'\b(ciao|salve|grazie|prego|io|capelli|trapianto|costo|prezzo|vorrei|ho bisogno|quanto|cos\'è|appuntamento)\b', re.I),
    "pt": re.compile(r'\b(olá|oi|obrigado|obrigada|por favor|eu|cabelo|transplante|custo|preço|gostaria|preciso|quanto|o que é|consulta)\b', re.I),
    "es": re.compile(r'\b(hola|buenos|gracias|por favor|yo|pelo|cabello|trasplante|costo|precio|quisiera|necesito|cuánto|qué es|cita)\b', re.I),
}

# ── Detección de interés real en trasplante / precios / info ─────
# Lista amplia: precios, procedimiento, médico, logística, cabello, alopecia
_INTEREST_PATTERNS = {
    "es": re.compile(
        r'\b(precio|precios|cuánto|cuanto|cuesta|coste|costo|presupuesto|tarifa|oferta|descuento|'
        r'trasplante|capilar|pelo|cabello|cabellos|calvicie|alopecia|entradas|coronilla|hairline|'
        r'fotos?|fotografía|fotografías|imagen|imágenes|'
        r'info|información|informacion|detalles|explicar|explicame|cuéntame|cuentame|'
        r'quiero|quisiera|necesito|me gustaría|interesa|interesado|interesada|'
        r'cita|consulta|reserva|cuando|cuándo|dónde|donde|cómo|como funciona|'
        r'turquía|turquia|estambul|istanbul|clínica|clinica|'
        r'doctor|médico|medico|cirugía|cirugia|operación|operacion|intervención|'
        r'injerto|folículo|foliculo|técnica|tecnica|fue|dhi|zafiro|sapphire|'
        r'resultados|antes y después|recuperación|recuperacion|postoperatorio|'
        r'anestesia|dolor|cicatriz|garantía|seguro|vuelos|vuelo|hotel|alojamiento|'
        r'todo incluido|pérdida|perdida|caída|caida|density|densidad|calidad|'
        r'sí|si|claro|desde luego|por supuesto|adelante|dime|cuéntame|explicame)\b',
        re.I),
    "en": re.compile(
        r'\b(price|prices|cost|costs|how much|budget|quote|fee|discount|offer|'
        r'transplant|hair|hair loss|hairline|baldness|alopecia|receding|crown|thinning|'
        r'photos?|pictures?|images?|'
        r'info|information|details|explain|tell me|tell us|'
        r'want|wanted|need|would like|interested|interest|'
        r'appointment|consultation|booking|book|when|where|how does it work|'
        r'turkey|istanbul|clinic|'
        r'doctor|physician|surgeon|surgery|operation|procedure|'
        r'graft|follicle|technique|fue|dhi|sapphire|'
        r'results|before and after|recovery|aftercare|'
        r'anesthesia|pain|scar|guarantee|insurance|flights|flight|hotel|accommodation|'
        r'all inclusive|density|quality|'
        r'yes|sure|absolutely|go ahead|ok|okay|please|more info|more details)\b',
        re.I),
    "de": re.compile(
        r'\b(preis|preise|kosten|wie viel|budget|angebot|rabatt|'
        r'transplantation|haar|haare|haarausfall|glatze|alopecia|haarlinie|'
        r'fotos?|bilder?|aufnahmen|'
        r'info|information|informationen|details|erklären|erzählen|'
        r'möchte|möchten|brauche|interessiert|interesse|'
        r'termin|beratung|buchung|wann|wo|wie funktioniert|'
        r'türkei|istanbul|klinik|'
        r'arzt|doktor|chirurg|operation|eingriff|verfahren|'
        r'transplantat|follikel|technik|fue|dhi|saphir|'
        r'ergebnisse|vorher nachher|erholung|nachsorge|'
        r'anästhesie|schmerz|narbe|garantie|versicherung|flüge|flug|hotel|unterkunft|'
        r'rundumservice|dichte|qualität|'
        r'ja|sicher|natürlich|bitte|mehr info|mehr details)\b',
        re.I),
    "fr": re.compile(
        r'\b(prix|coût|coûts|combien|budget|devis|remise|offre|'
        r'transplantation|greffe|cheveux|chute|calvitie|alopécie|ligne|'
        r'photos?|images?|clichés|'
        r'info|information|informations|détails|expliquer|dites-moi|'
        r'veux|voudrais|besoin|intéressé|intéressée|intérêt|'
        r'rendez-vous|consultation|réservation|quand|où|comment|'
        r'turquie|istanbul|clinique|'
        r'médecin|docteur|chirurgien|chirurgie|opération|procédure|'
        r'greffe|follicule|technique|fue|dhi|saphir|'
        r'résultats|avant après|récupération|suivi|'
        r'anesthésie|douleur|cicatrice|garantie|assurance|vols|vol|hôtel|hébergement|'
        r'tout compris|densité|qualité|'
        r'oui|bien sûr|absolument|allez-y|ok|plus d.info)\b',
        re.I),
    "it": re.compile(
        r'\b(prezzo|prezzi|costo|costi|quanto costa|budget|preventivo|sconto|offerta|'
        r'trapianto|capelli|perdita|calvizie|alopecia|attaccatura|'
        r'foto|immagini|'
        r'info|informazioni|dettagli|spiegare|dimmi|'
        r'voglio|vorrei|ho bisogno|interessato|interessata|interesse|'
        r'appuntamento|consulenza|prenotazione|quando|dove|come funziona|'
        r'turchia|istanbul|clinica|'
        r'medico|dottore|chirurgo|chirurgia|operazione|procedura|'
        r'innesto|follicolo|tecnica|fue|dhi|zaffiro|'
        r'risultati|prima e dopo|recupero|cura post|'
        r'anestesia|dolore|cicatrice|garanzia|assicurazione|voli|volo|hotel|alloggio|'
        r'tutto incluso|densità|qualità|'
        r'sì|certo|assolutamente|ok|più info)\b',
        re.I),
    "pt": re.compile(
        r'\b(preço|preços|custo|custos|quanto custa|orçamento|desconto|oferta|'
        r'transplante|cabelo|queda|calvície|alopecia|entradas|'
        r'fotos?|imagens?|fotografias?|'
        r'info|informação|informações|detalhes|explicar|diz-me|'
        r'quero|gostaria|preciso|interessado|interessada|interesse|'
        r'consulta|marcação|reserva|quando|onde|como funciona|'
        r'turquia|istanbul|clínica|'
        r'médico|doutor|cirurgião|cirurgia|operação|procedimento|'
        r'enxerto|folículo|técnica|fue|dhi|safira|'
        r'resultados|antes e depois|recuperação|pós-operatório|'
        r'anestesia|dor|cicatriz|garantia|seguro|voos|voo|hotel|alojamento|'
        r'tudo incluído|densidade|qualidade|'
        r'sim|claro|com certeza|ok|mais info)\b',
        re.I),
}

def _detecta_interes(text: str, lang: str = "es") -> bool:
    """True si el texto muestra interés en trasplante, precios o información clínica."""
    if not text or len(text) < 2:
        return False
    pattern = _INTEREST_PATTERNS.get(lang, _INTEREST_PATTERNS["en"])
    return bool(pattern.search(text))

def detect_language(text: str, phone: str, history_lang: str = "") -> str:
    """
    Detecta idioma: historial > texto del mensaje > prefijo de país > español.
    Si el número no tiene prefijo reconocido se asume español (España / LATAM).
    """
    if history_lang:
        return history_lang

    if text and len(text) > 3:
        scores = {lang: len(pat.findall(text)) for lang, pat in _LANG_PATTERNS.items()}
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best

    # Fallback: prefijo de país (más largo primero para evitar ambigüedad)
    digits = re.sub(r'\D', '', phone)
    for prefix in sorted(config.PREFIX_LANG.keys(), key=len, reverse=True):
        if digits.startswith(prefix):
            return config.PREFIX_LANG[prefix]

    # Sin prefijo reconocido → español por defecto
    # (números locales sin + ni código de país son casi siempre Spain/LATAM)
    return "es"

_BASE = os.path.dirname(os.path.abspath(__file__))

TZ = ZoneInfo("Atlantic/Canary")
HORA_MIN = (8, 30)   # 08:30
HORA_MAX = (20, 0)   # 20:00
MIN_ESPERA_H = 0.167 if config.TEST_MODE else 4  # 10 min en test, 4h en producción

def _en_horario(dt=None):
    """True si el momento (hora Canarias) está en franja permitida 08:30–20:00."""
    if config.TEST_MODE:
        return True  # Sin restricción horaria en modo test
    dt = dt or datetime.now(TZ)
    minutos = dt.hour * 60 + dt.minute
    return HORA_MIN[0] * 60 + HORA_MIN[1] <= minutos < HORA_MAX[0] * 60 + HORA_MAX[1]

def _siguiente_momento_valido(ts_fotos: float) -> datetime:
    """
    Devuelve el datetime (Canarias) más próximo en que se pueden enviar ambas
    condiciones cumplidas: ≥8h desde fotos Y dentro de 08:30–20:00.
    """
    minimo_por_espera = datetime.fromtimestamp(ts_fotos, TZ) + timedelta(hours=MIN_ESPERA_H)
    candidato = max(minimo_por_espera, datetime.now(TZ))

    # Ajustar a franja horaria
    for _ in range(3):  # máximo 3 iteraciones (cubre siempre)
        minutos = candidato.hour * 60 + candidato.minute
        min_ok  = HORA_MIN[0] * 60 + HORA_MIN[1]
        max_ok  = HORA_MAX[0] * 60 + HORA_MAX[1]
        if minutos < min_ok:
            candidato = candidato.replace(hour=HORA_MIN[0], minute=HORA_MIN[1], second=0, microsecond=0)
        elif minutos >= max_ok:
            candidato = (candidato + timedelta(days=1)).replace(
                hour=HORA_MIN[0], minute=HORA_MIN[1], second=0, microsecond=0)
        else:
            break
    return candidato

app = Flask(__name__)

_media_lock   = threading.Lock()           # evita race condition con fotos simultáneas
_leads_wa_lock = threading.Lock()          # protege escrituras en nuevos_leads_wa.csv

# ─── Registro de leads WA ─────────────────────────────────────────
_WA_LEADS_FIELDS = [
    "cliente_num", "nombre", "telefono", "telefonos_extra",
    "email", "tipo", "segmento", "notas", "canal", "fecha_entrada",
]

def _get_next_cliente_num() -> int:
    """Lee y actualiza el contador correlativo en disco (empieza en 6927)."""
    with _leads_wa_lock:
        data = _load(config.LAST_NUM_FILE, {"ultimo": 6927})
        data["ultimo"] += 1
        _save(config.LAST_NUM_FILE, data)
        return data["ultimo"]

def _register_wa_lead(phone: str, lang: str, timestamp: int) -> str:
    """
    Registra nuevo lead en nuevos_leads_wa.csv.
    Devuelve el prefijo asignado (p.ej. 'Cliente06928').
    """
    num    = _get_next_cliente_num()
    prefijo = f"Cliente{num:05d}"
    fecha  = datetime.fromtimestamp(timestamp, TZ).strftime("%Y-%m-%d %H:%M")

    wa_file = config.WA_LEADS_FILE
    row = {
        "cliente_num":     str(num),
        "nombre":          f"{prefijo} (sin nombre)",
        "telefono":        phone,
        "telefonos_extra": "",
        "email":           "",
        "tipo":            "clinica",
        "segmento":        "WA_AUTO",
        "notas":           f"idioma:{lang}",
        "canal":           "WA_AUTO",
        "fecha_entrada":   fecha,
    }
    with _leads_wa_lock:
        file_exists = os.path.exists(wa_file)
        with open(wa_file, "a", newline="", encoding="utf-8") as f:
            writer = csv_mod.DictWriter(f, fieldnames=_WA_LEADS_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    print(f"[REGISTRO] {prefijo} → {phone} (idioma:{lang})")
    return prefijo

def _update_wa_lead(phone: str, nombre: str = None, email: str = None):
    """Actualiza nombre o email de un lead ya registrado en nuevos_leads_wa.csv."""
    wa_file = config.WA_LEADS_FILE
    if not os.path.exists(wa_file):
        return
    with _leads_wa_lock:
        with open(wa_file, newline="", encoding="utf-8") as f:
            rows = list(csv_mod.DictReader(f))
        changed = False
        for row in rows:
            if row.get("telefono") == phone:
                if nombre and "(sin nombre)" in row.get("nombre", ""):
                    prefix_m = re.match(r'(Cliente\d{5})', row["nombre"])
                    pref = prefix_m.group(1) if prefix_m else ""
                    # Title case del nombre
                    nombre_tc = " ".join(
                        (t[0].upper() + t[1:].lower()) for t in nombre.split()
                    )
                    row["nombre"] = f"{pref} {nombre_tc}".strip()
                    changed = True
                if email and not row.get("email"):
                    row["email"] = email
                    changed = True
                break
        if changed and rows:
            with open(wa_file, "w", newline="", encoding="utf-8") as f:
                writer = csv_mod.DictWriter(f, fieldnames=_WA_LEADS_FIELDS)
                writer.writeheader()
                writer.writerows(rows)

# ─── Estado en disco ──────────────────────────────────────────────
def _load(path, default):
    return json.load(open(path)) if os.path.exists(path) else default

def _save(path, data):
    json.dump(data, open(path, "w"), indent=2, ensure_ascii=False)

def load_state():  return _load(config.STATE_FILE, {})
def save_state(s): _save(config.STATE_FILE, s)
def load_media():  return _load(config.MEDIA_CACHE, {})

def norm(num):
    """Normaliza número a formato +34XXXXXXXXX"""
    num = str(num).strip()
    return num if num.startswith("+") else "+" + num

# ─── Cola de mensajes para mercados internacionales sin servidor 24/7 ─────
_INTL_QUEUE_LOCK = threading.Lock()

def _sheets_service_intl():
    """Reutiliza las credenciales de Google ya usadas por review_requests.py."""
    from google.oauth2.credentials import Credentials as _Creds
    from googleapiclient.discovery import build as _build
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if refresh_token and client_id and client_secret:
        creds = _Creds(
            token=None, refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id, client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
    else:
        tok = _load(os.path.join(_BASE, "..", "credentials", "google_tokens.json"), {})
        creds = _Creds(
            token=tok.get("access_token"), refresh_token=tok.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=tok.get("client_id"), client_secret=tok.get("client_secret"),
            scopes=tok.get("scope", "").split(),
        )
    return _build("sheets", "v4", credentials=creds)

def _queue_mercado_internacional(from_num: str, lang: str, body: str, msg_type: str, timestamp: int):
    """
    Deposita un mensaje entrante de un mercado sin servidor 24/7 propio (Italia,
    Inglés) en una cola compartida (Google Sheet) para que esa sesión lo procese
    en su próximo ciclo de loop, en vez de responder con la plantilla genérica
    de España (dominio/precio equivocados para ese mercado).
    """
    mercado = config.INTL_MARKET_QUEUE.get(lang, lang)
    texto = body if body else f"[{msg_type} recibido, sin texto]"
    fecha = datetime.fromtimestamp(timestamp, TZ).strftime("%Y-%m-%d %H:%M")
    row = [fecha, from_num, mercado, lang, texto, "pendiente", ""]
    try:
        with _INTL_QUEUE_LOCK:
            service = _sheets_service_intl()
            service.spreadsheets().values().append(
                spreadsheetId=config.INTL_QUEUE_SHEET_ID,
                range="Cola!A:G",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]},
            ).execute()
        print(f"[INTL_QUEUE] {from_num} ({mercado}/{lang}) → depositado en cola")
    except Exception as e:
        print(f"[INTL_QUEUE] ERROR depositando {from_num} ({mercado}): {e}")

# ─── Webhook Meta: verificación GET ──────────────────────────────
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == config.VERIFY_TOKEN:
        return request.args.get("hub.challenge", "")
    return "Forbidden", 403

# ─── Webhook Meta: mensajes POST ─────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                # Procesar en hilo separado para responder a Meta en <5s
                threading.Thread(target=process_message, args=(msg,), daemon=True).start()
    return jsonify({"status": "ok"})

# ─── Procesador principal ─────────────────────────────────────────
def process_message(msg):
    from_raw  = msg.get("from", "")
    from_num  = norm(from_raw)
    msg_type  = msg.get("type", "")
    timestamp = int(msg.get("timestamp", time.time()))

    print(f"[MSG] {from_num} | tipo={msg_type}")

    # ── Comando del admin (648) ──────────────────────────────────
    if from_num == config.ADMIN_NUMBER and msg_type == "text":
        body = msg.get("text", {}).get("body", "").strip()
        if body.startswith("##"):
            handle_admin_command(body[2:].strip())
            return

    # ── Mensajes de leads ────────────────────────────────────────
    state = load_state()
    lead  = state.get(from_num, {})
    body  = msg.get("text", {}).get("body", "").strip() if msg_type == "text" else ""

    # Detectar idioma (política: mensaje > historial > país)
    lang = detect_language(body, from_num, lead.get("idioma", ""))

    # ── Enrutamiento hub central: mercados con sesión propia (sin servidor 24/7) ──
    # Italia e Inglés no tienen infraestructura propia para escuchar webhooks;
    # España actúa de hub y deposita estos leads en una cola compartida (Sheet)
    # en vez de responder con la plantilla genérica (que enlaza al dominio de España).
    # Ver memoria: project_ghh_whatsapp_hub_central_multimercado.
    if lang in config.INTL_MARKET_QUEUE:
        _queue_mercado_internacional(from_num, lang, body, msg_type, timestamp)
        return

    estado = lead.get("estado", "")

    if msg_type in ("image", "video"):
        handle_media(from_num, msg, msg_type, lead, state)

    elif not lead:
        # Primera vez que nos escribe (inbound) → secuencia automática
        send_auto_sequence(from_num, lang)
        prefijo = _register_wa_lead(from_num, lang, timestamp)
        state[from_num] = {
            "estado": "auto_enviado",
            "timestamp_contacto": timestamp,
            "nombre": "", "email": "",
            "foliculos": None, "tecnica": None,
            "idioma": lang, "cliente_prefijo": prefijo,
        }
        save_state(state)

    elif estado == "cebo_enviado" and msg_type == "text":
        # Contacto proactivo que nos responde → detectar interés
        lead["idioma"] = lang
        if _detecta_interes(body, lang):
            # Interés detectado → enviar secuencia completa
            send_auto_sequence(from_num, lang)
            lead["estado"] = "auto_enviado"
            lead["timestamp_contacto"] = timestamp
        elif body.upper().strip() in ("AUDIO", "AUDIO.", "SI", "SÍ", "YES", "JA", "OUI", "SIM"):
            _send_audio_celik(from_num, lang)
        else:
            # Sin interés claro → respuesta cálida, no enviamos secuencia
            wa_api.send_text(from_num, config.get_msgs(lang)["no_interes"])
            lead["estado"] = "sin_interes"
        state[from_num] = lead
        save_state(state)

    elif msg_type == "text" and body:
        updated = False
        # Comando AUDIO en cualquier estado
        if body.upper().strip() in ("AUDIO", "AUDIO."):
            _send_audio_celik(from_num, lang)
            updated = False
        elif "@" in body and "." in body and not lead.get("email"):
            lead["email"] = body
            _update_wa_lead(from_num, email=body)
            updated = True
        elif len(body) > 3 and not lead.get("nombre") and "@" not in body:
            lead["nombre"] = body
            _update_wa_lead(from_num, nombre=body)
            updated = True
        if lang != lead.get("idioma") and len(body) > 5:
            lead["idioma"] = lang
            updated = True
        if updated:
            state[from_num] = lead
            save_state(state)

# ─── Audio bajo demanda del Dr. Çelik ────────────────────────────
def _send_audio_celik(to: str, lang: str):
    """Envía la grabación de voz cuando el contacto la solicita con AUDIO."""
    media = load_media()
    audio_id = media.get("audio_id") if lang == "es" else media.get("audio_en_id")
    if audio_id:
        wa_api.send_audio(to, audio_id)
    else:
        print(f"[AUDIO] Sin audio_id en cache para lang={lang}")

# ─── Secuencia automática de 7 mensajes ──────────────────────────
def send_auto_sequence(to, lang="es"):
    media = load_media()
    m = config.get_msgs(lang)
    if not media.get("cert_1_id"):
        print("⚠️  media_cache.json vacío — subiendo automáticamente...")
        _ensure_media_cache()
        media = load_media()
    if not media.get("cert_1_id"):
        wa_api.send_text(to, m["p1"])
        return

    wa_api.send_text(to, m["p1"]);                 time.sleep(1.5)
    wa_api.send_text(to, m["p2"]);                 time.sleep(1.5)
    wa_api.send_text(to, m["p3"]);                 time.sleep(1.5)
    wa_api.send_document(to, media["cert_1_id"],
        "Certificado_MD_Dr_Celik.pdf");             time.sleep(1.5)
    wa_api.send_document(to, media["cert_2_id"],
        "Certificado_Medicina_Estetica.pdf");       time.sleep(1.5)
    wa_api.send_video(to, media["video_id"]);      time.sleep(1.5)
    # Audio bajo demanda — el contacto responde AUDIO si quiere escucharlo
    m_audio = config.get_msgs(lang)
    wa_api.send_text(to, m_audio["audio_oferta"])
    print(f"[AUTO] Secuencia enviada a {to} (idioma: {lang})")

# ─── Reenvío de fotos al admin ────────────────────────────────────
def handle_media(from_num, msg, msg_type, lead, state):
    media_id = msg.get(msg_type, {}).get("id")
    if not media_id:
        return

    with _media_lock:
        # Recargar estado dentro del lock para evitar race condition
        state = load_state()
        lead  = state.get(from_num, {})
        primera_vez = lead.get("estado") != "fotos_recibidas"

        if primera_vez:
            nombre = lead.get("nombre") or from_num
            wa_api.send_text(
                config.ADMIN_NUMBER,
                f"📸 *Fotos recibidas*\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"👤 Lead: {nombre}\n"
                f"📱 Tel: {from_num}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"1️⃣ Reenvía las fotos al grupo clínica\n"
                f"2️⃣ Copia el mensaje siguiente, rellena folículos y nombre, y envíalo aquí."
            )
            time.sleep(0.8)
            wa_api.send_text(
                config.ADMIN_NUMBER,
                f"✏️ Completa los dos campos y envía:\n\n"
                f"👤 Nombre    → [ ]\n"
                f"📋 Folículos → [ ]\n\n"
                f"##[ ] {from_num} [ ]"
            )
            lead["estado"] = "fotos_recibidas"

        # Actualizar timestamp con cada foto — el timer siempre cuenta desde la última
        lead["timestamp_fotos"] = time.time()
        lead["n_fotos"] = lead.get("n_fotos", 0) + 1
        state[from_num] = lead
        save_state(state)

        # Timers persistentes — sobreviven a reinicios del servidor
        if primera_vez:
            now = time.time()
            if config.TEST_MODE:
                scheduler.schedule(from_num, "fotos_ok",    fire_at=now + 600)   # 10 min (test)
                scheduler.schedule(from_num, "pedir_datos", fire_at=now + 600)   # 10 min (test)
            else:
                scheduler.schedule(from_num, "fotos_ok",    fire_at=now + 600)   # 10 min
                scheduler.schedule(from_num, "pedir_datos", fire_at=now + 1800)  # 30 min

    # Reenviar la foto/vídeo al admin (fuera del lock — no bloquea las siguientes)
    wa_api.forward_image(config.ADMIN_NUMBER, media_id, f"📸 {from_num}")
    print(f"[FOTO] {from_num} → reenviada al admin (foto #{lead.get('n_fotos', '?')})")

# ─── Envío por email (solo si tenemos email del lead) ────────────
def _enviar_por_email(email_destino: str, nombre: str, pdf_path: str):
    """Pendiente: configurar Gmail App Password en credentials."""
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email.mime.text import MIMEText
        from email import encoders

        gmail_user = os.environ.get("GMAIL_USER", "sergimaymo@gmail.com")
        gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
        if not gmail_pass:
            creds_path = os.path.join(_BASE, "../credentials/meta_tokens.json")
            if os.path.exists(creds_path):
                _CREDS = json.load(open(creds_path))
                gmail_user = _CREDS.get("gmail_user", gmail_user)
                gmail_pass = _CREDS.get("gmail_app_password", "")
        if not gmail_pass:
            print("[EMAIL] Sin App Password configurada — saltando email")
            return

        msg = MIMEMultipart()
        msg["From"]    = gmail_user
        msg["To"]      = email_destino
        msg["Subject"] = "Su informe de diagnóstico capilar — Global Health Hair"

        saludo = f"Estimado/a {nombre},\n\n" if nombre else "Estimado/a cliente,\n\n"
        msg.attach(MIMEText(
            saludo +
            "Adjunto encontrará su informe de diagnóstico capilar personalizado.\n\n"
            "Quedamos a su disposición para cualquier consulta.\n\n"
            "Global Health Hair Istanbul\n"
            "www.trasplantepeloturquia.com",
            "plain", "utf-8"
        ))

        with open(pdf_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        fname = f"Informe_GHH_{nombre.split()[0] if nombre else 'Diagnostico'}.pdf"
        part.add_header("Content-Disposition", f'attachment; filename="{fname}"')
        msg.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, email_destino, msg.as_string())
        print(f"[EMAIL] Informe enviado a {email_destino}")
    except Exception as e:
        print(f"[EMAIL] Error: {e}")

# ─── Envío diferido de informe ────────────────────────────────────
def _enviar_informe_diferido(lead_phone, nombre, foliculos, tecnica, espera_s, state):
    time.sleep(espera_s)
    primer = nombre.split()[0] if nombre else "Diagnostico"
    label  = nombre if nombre else "(sin nombre)"
    try:
        pdf_path = generate_informe(nombre, foliculos, tecnica)
        media_id = wa_api.upload_media(pdf_path, "application/pdf")
        wa_api.send_document(
            lead_phone, media_id,
            f"Informe_GHH_{primer}.pdf",
            f"Su informe de diagnóstico capilar — {foliculos} folículos"
        )
        time.sleep(1.5)
        wa_api.send_text(lead_phone, config.MSG_INFORME)

        lead  = load_state().get(lead_phone, {})
        email = lead.get("email", "")
        if email:
            _enviar_por_email(email, nombre, pdf_path)

        wa_api.send_text(
            config.ADMIN_NUMBER,
            f"✅ *Informe enviado* (programado)\n"
            f"👤 {label} · {lead_phone}\n"
            f"📧 Email: {email if email else '— no disponible'}"
        )
        lead.update({"estado": "informe_enviado", "foliculos": foliculos, "tecnica": tecnica, "nombre": nombre})
        state[lead_phone] = lead
        save_state(state)
    except Exception as e:
        wa_api.send_text(config.ADMIN_NUMBER, f"❌ Error en informe diferido: {e}")
        print(f"[ERROR] informe diferido: {e}")

# ─── Comando ## desde el 648 ──────────────────────────────────────
def handle_admin_command(cmd):
    """
    Formato: Nombre +34XXXXXXXXX FOLICULOS
    Ejemplo: Juan García +34612345678 4500
    El informe siempre es DHI — el doctor decide en clínica.
    """
    parts = cmd.split()
    # Localizar el teléfono (token que empieza por +) como separador
    phone_idx = next((i for i, p in enumerate(parts) if p.startswith("+")), None)
    if phone_idx is None or phone_idx >= len(parts) - 1:
        wa_api.send_text(
            config.ADMIN_NUMBER,
            "⚠️ Formato incorrecto.\n"
            "Usa: ##[Nombre] +34XXXXXXXXX folículos\n"
            "Ej:  ##Juan García +34612345678 4500\n"
            "     ##  +34612345678 4500  (sin nombre)"
        )
        return

    nombre_cmd = " ".join(parts[:phone_idx])     # "Juan García" o ""
    lead_phone = norm(parts[phone_idx])           # "+34612345678"
    foliculos  = parts[phone_idx + 1]             # "4500"
    tecnica    = "DHI"                            # siempre DHI

    state  = load_state()
    lead   = state.get(lead_phone, {})
    nombre = nombre_cmd or lead.get("nombre") or ""   # vacío si no hay nombre

    # ── Validar restricciones de tiempo ──────────────────────────
    ts_fotos = lead.get("timestamp_fotos") or lead.get("timestamp_contacto", time.time())
    ahora    = datetime.now(TZ)
    horas_pasadas = (ahora.timestamp() - ts_fotos) / 3600

    if horas_pasadas < MIN_ESPERA_H or not _en_horario(ahora):
        momento = _siguiente_momento_valido(ts_fotos)
        espera_s = max(0, (momento - ahora).total_seconds())
        wa_api.send_text(
            config.ADMIN_NUMBER,
            f"⏰ *Informe programado*\n"
            f"👤 {nombre} · {lead_phone}\n"
            f"💊 {foliculos} folículos · {tecnica}\n\n"
            f"Se enviará el *{momento.strftime('%d/%m a las %H:%M')}* (hora Canarias)\n"
            f"{'— Mín. 8h desde fotos aún no cumplidas' if horas_pasadas < MIN_ESPERA_H else ''}"
            f"{'— Fuera de horario (08:30–20:00)' if not _en_horario(ahora) else ''}"
        )
        scheduler.schedule(lead_phone, "informe_diferido",
            fire_at=momento.timestamp(),
            nombre=nombre, foliculos=foliculos, tecnica=tecnica)
        return

    label = nombre if nombre else "(sin nombre)"
    wa_api.send_text(config.ADMIN_NUMBER, f"⏳ Generando informe para {label} ({lead_phone})...")

    try:
        pdf_path = generate_informe(nombre, foliculos, tecnica)
        media_id = wa_api.upload_media(pdf_path, "application/pdf")

        primer = nombre.split()[0] if nombre else "Diagnostico"
        wa_api.send_document(
            lead_phone, media_id,
            f"Informe_GHH_{primer}.pdf",
            f"Su informe de diagnóstico capilar — {foliculos} folículos"
        )
        time.sleep(1.5)
        wa_api.send_text(lead_phone, config.MSG_INFORME)

        # Email solo si tenemos dirección
        email = lead.get("email", "")
        if email:
            _enviar_por_email(email, nombre, pdf_path)

        # Confirmar al admin
        wa_api.send_text(
            config.ADMIN_NUMBER,
            f"✅ *Informe enviado*\n"
            f"👤 {label} · {lead_phone}\n"
            f"📧 Email: {email if email else '—  no disponible'}"
        )

        lead.update({"estado": "informe_enviado", "foliculos": foliculos, "tecnica": tecnica, "nombre": nombre})
        state[lead_phone] = lead
        save_state(state)

    except Exception as e:
        wa_api.send_text(config.ADMIN_NUMBER, f"❌ Error generando informe: {e}")
        print(f"[ERROR] informe: {e}")

# ─── Endpoint: descarga de leads WA ──────────────────────────────
@app.route("/export/leads", methods=["GET"])
def export_leads():
    """
    Descarga nuevos_leads_wa.csv para fusionar con el master local.
    Protegido con ?token=VERIFY_TOKEN
    """
    if request.args.get("token", "") != config.VERIFY_TOKEN:
        return "Forbidden", 403
    wa_file = config.WA_LEADS_FILE
    if not os.path.exists(wa_file):
        return "Sin leads WA aún.", 200, {"Content-Type": "text/plain; charset=utf-8"}
    with open(wa_file, "r", encoding="utf-8") as f:
        content = f.read()
    return content, 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="nuevos_leads_wa.csv"',
    }

# ─── Arranque ────────────────────────────────────────────────────
def _ensure_media_cache():
    """Si el cache de media está vacío o incompleto, sube los archivos estáticos automáticamente."""
    media = load_media()
    if not media.get("cert_1_id"):
        print("[STARTUP] media_cache.json vacío — subiendo archivos estáticos a Meta...")
        try:
            from upload_media import upload_all
            upload_all()
            print("[STARTUP] ✅ Archivos estáticos subidos correctamente")
        except Exception as e:
            print(f"[STARTUP] ⚠️  Error subiendo media: {e}")
        media = load_media()

    # Subir audio inglés si aún no está en cache (añadido 21-jun-2026)
    if not media.get("audio_en_id") and os.path.exists(config.AUDIO_EN_PATH):
        print("[STARTUP] Subiendo audio_en.m4a a Meta...")
        try:
            audio_en_id = wa_api.upload_media(config.AUDIO_EN_PATH, "audio/mp4")
            media["audio_en_id"] = audio_en_id
            _save(config.MEDIA_CACHE, media)
            print(f"[STARTUP] ✅ audio_en_id guardado: {audio_en_id}")
        except Exception as e:
            print(f"[STARTUP] ⚠️  Error subiendo audio_en: {e}")

if __name__ == "__main__":
    _ensure_media_cache()   # Auto-upload media si cache vacío
    scheduler.recover()     # Capa 1: recuperar timers pendientes tras reinicio

    # Auditoria diaria SEO+SEM 07:00 Atlantic/Canary (Railway 24/7, Mac puede estar apagado)
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from audit_seo_sem import run_daily_audit
        from clinic_emails import run_clinic_liquidation_emails, run_clinic_reminder_emails
        from x_bot import run_x_bot_cycle
        from review_requests import run_review_requests
        _bg = BackgroundScheduler(timezone="Atlantic/Canary")
        _bg.add_job(run_daily_audit, CronTrigger(hour=7, minute=0))
        # Emails clínica pre-llegada (Canary = Madrid-1h en verano)
        _bg.add_job(run_clinic_reminder_emails, CronTrigger(hour=7, minute=0))
        _bg.add_job(run_clinic_liquidation_emails, CronTrigger(hour=9, minute=0))
        # Solicitud automática de reseñas (Google+Trustpilot) — pacientes con check-in ayer
        _bg.add_job(run_review_requests, CronTrigger(hour=10, minute=0))
        # X/Twitter bot — comprueba cada 30min si es ventana óptima para publicar (máx 2/día)
        from apscheduler.triggers.interval import IntervalTrigger
        _bg.add_job(run_x_bot_cycle, IntervalTrigger(minutes=30))
        _bg.start()
        print("Auditoria diaria SEO/SEM programada 07:00 Atlantic/Canary")
        print("Emails clinica: recordatorio 07:00, liquidaciones 09:00 Atlantic/Canary")
        print("Solicitud de reseñas (Google+Trustpilot): diario 10:00 Atlantic/Canary")
        print("X/Twitter bot: ciclo cada 30min (max 2 tweets/dia en horas optimas)")
    except Exception as e:
        print(f"No se pudo iniciar audit scheduler: {e}")

    port = int(os.environ.get("PORT", 5001))
    print(f"GHH Webhook WB arrancando en http://localhost:{port}/webhook")
    app.run(host="0.0.0.0", port=port, debug=False)
