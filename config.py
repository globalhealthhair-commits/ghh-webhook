import json, os

# ── Detección de entorno ──────────────────────────────────────────
_BASE      = os.path.dirname(os.path.abspath(__file__))
# Cualquier hosting con las credenciales en variables de entorno (Railway, Render, etc.)
_HAS_ENV_CREDS = bool(os.environ.get("WA_TOKEN"))

# TEST_MODE: False en produccion (con env vars), True solo en local sin credenciales
TEST_MODE = not _HAS_ENV_CREDS

# ── Credenciales: env vars en produccion, JSON en local ──────────────
def _env(key, fallback=None):
    return os.environ.get(key, fallback)

if _HAS_ENV_CREDS:
    WA_TOKEN   = _env("WA_TOKEN")
    WABA_ID    = _env("WABA_ID")
    TG_TOKEN   = _env("TG_TOKEN")
    TG_CHAT_ID = int(_env("TG_CHAT_ID", "0"))
    GMAIL_USER = _env("GMAIL_USER", "sergimaymo@gmail.com")
    GMAIL_PASS = _env("GMAIL_APP_PASSWORD", "")
else:
    _CREDS     = json.load(open(os.path.join(_BASE, "../credentials/meta_tokens.json")))
    WA_TOKEN   = _CREDS["wa_system_user_token"]
    WABA_ID    = _CREDS["waba_id"]
    TG_TOKEN   = _CREDS["telegram_bot_token"]
    TG_CHAT_ID = _CREDS["telegram_chat_id"]
    GMAIL_USER = _CREDS.get("gmail_user", "sergimaymo@gmail.com")
    GMAIL_PASS = _CREDS.get("gmail_app_password", "")

# ── WhatsApp API ──────────────────────────────────────────────────
PHONE_ID = "1090254980847119"   # +34 638 58 00 88

# ── Números clave ─────────────────────────────────────────────────
ADMIN_NUMBER  = "+34648423777"   # Sergi — recibe alertas y manda ##comandos
CLINIC_NUMBER = "+905449544363"  # Grupo clínica Estambul (info)

# ── Rutas de archivos ─────────────────────────────────────────────
# DATA_DIR: persistente en Railway Volume (/app/data), local en ./data
DATA_DIR      = _env("DATA_DIR", os.path.join(_BASE, "data"))
os.makedirs(DATA_DIR, exist_ok=True)

STATE_FILE    = os.path.join(DATA_DIR, "estado_leads.json")
MEDIA_CACHE   = os.path.join(DATA_DIR, "media_cache.json")
PENDING_FILE  = os.path.join(DATA_DIR, "pending_actions.json")
WA_LEADS_FILE = os.path.join(DATA_DIR, "nuevos_leads_wa.csv")
LAST_NUM_FILE = os.path.join(DATA_DIR, "last_cliente_num.json")

# Archivos estáticos — incluidos en el repo
STATIC_DIR    = os.path.join(_BASE, "static")
CERT_1_PATH   = os.path.join(STATIC_DIR, "cert_1.pdf")
CERT_2_PATH   = os.path.join(STATIC_DIR, "cert_2.pdf")
AUDIO_PATH    = os.path.join(STATIC_DIR, "audio.m4a")      # Grabación en español
AUDIO_EN_PATH = os.path.join(STATIC_DIR, "audio_en.m4a")  # Grabación en inglés (todos los demás idiomas)
VIDEO_PATH    = os.path.join(STATIC_DIR, "video.mp4")
TEMPLATE_PATH = os.path.join(_BASE, "INFORME-TEMPLATE.docx")

# ── Webhook ───────────────────────────────────────────────────────
VERIFY_TOKEN = _env("VERIFY_TOKEN", "ghh_webhook_2026_secure")

# ── Textos automáticos multiidioma ───────────────────────────────
# Política: idioma del mensaje > historial > código de país
# Idiomas soportados: es, en, de, fr, it, pt

MSGS = {
    "es": {
        "p1": 'Está contactando con la clínica de trasplante capilar "Global Health Istanbul / Dr. Merdan Çelik"',
        "p2": (
            "Proceso sencillo y rápido:\n\n"
            "1️⃣ Envíenos 6-7 fotos de su cabello (frente, laterales, coronilla y parte trasera) sin flash.\n\n"
            "2️⃣ Indíquenos su nombre completo y correo electrónico.\n\n"
            "En 24-48 horas, nuestro equipo médico le enviará un informe detallado.\n\n"
            "📩 Después, estaremos encantados de resolver cualquier duda.\n\n"
            "https://trasplantepeloturquia.com/\n\n"
            "Premium: 1.990€ – Todo incluido (sin vuelos).\n"
            "Premium +: 2.390€ – Todo incluido (con vuelos)."
        ),
        "p3": (
            "Antes de decidir, le recomendamos comprobar las certificaciones del doctor que realizará "
            "la intervención. En Turquía, el requisito médico legal mínimo es ser MD – Tıp Doktoru, "
            "algo que no siempre se revisa al comparar clínicas. Si lo desea, podemos ayudarle a "
            "verificarlo de forma sencilla.\n\n"
            "Si tuviera alguna pregunta, por favor háganosla saber para poder responderle. Gracias."
        ),
        "fotos_ok": (
            "Fotografías correctas. En un máximo de 24 horas recibirá el informe del doctor; "
            "le agradeceríamos confirmación de recepción. "
            "Quedamos a su disposición para cualquier consulta."
        ),
        "pedir_datos": "También necesitaríamos su nombre y correo electrónico.",
        "informe": (
            "Informe enviado por WhatsApp y correo; agradecemos confirmación. "
            "Procedimiento bajo doctor MD (Tıp Doktoru), requisito legal en Turquía. "
            "Opciones: Premium 1.990€ o Premium Plus 2.390€. "
            "Si necesitara coordinar una llamada nos lo indica, así como fechas de viaje. Gracias."
        ),
        "audio_oferta": (
            "🎙️ Si deseas escuchar un breve mensaje de voz del Dr. Çelik, responde *AUDIO* y te lo enviamos ahora."
        ),
        "no_interes": (
            "¡Perfecto! Te mantendremos informado de nuestras promociones y novedades 😊\n"
            "Cuando quieras más información, escríbenos sin compromiso."
        ),
    },
    "en": {
        "p1": 'You are contacting the hair transplant clinic "Global Health Istanbul / Dr. Merdan Çelik"',
        "p2": (
            "Simple and quick process:\n\n"
            "1️⃣ Send us 6-7 photos of your hair (front, sides, crown and back) without flash.\n\n"
            "2️⃣ Tell us your full name and email address.\n\n"
            "Within 24-48 hours, our medical team will send you a detailed report.\n\n"
            "📩 Afterwards, we'll be happy to answer any questions.\n\n"
            "https://trasplantepeloturquia.com/\n\n"
            "Premium: 1,990€ – All inclusive (flights not included).\n"
            "Premium +: 2,390€ – All inclusive (flights included up to 400€)."
        ),
        "p3": (
            "Before deciding, we recommend checking the certifications of the doctor who will perform "
            "the procedure. In Turkey, the minimum legal medical requirement is to be an MD – Tıp Doktoru, "
            "something that is not always verified when comparing clinics. If you wish, we can help you "
            "verify this easily.\n\n"
            "If you have any questions, please let us know. Thank you."
        ),
        "fotos_ok": (
            "Photos received correctly. You will receive the doctor's report within 24 hours; "
            "we would appreciate confirmation of receipt. "
            "We remain at your disposal for any queries."
        ),
        "pedir_datos": "We would also need your full name and email address.",
        "informe": (
            "Report sent via WhatsApp and email; we appreciate confirmation. "
            "Procedure performed by a licensed MD (Tıp Doktoru), legal requirement in Turkey. "
            "Options: Premium 1,990€ or Premium Plus 2,390€. "
            "If you need to arrange a call, please let us know along with your travel dates. Thank you."
        ),
        "audio_oferta": (
            "🎙️ Would you like to hear a short voice message from Dr. Çelik? Reply *AUDIO* and we'll send it right away."
        ),
        "no_interes": (
            "Great! We'll keep you updated on our promotions and news 😊\n"
            "Feel free to reach out anytime with no commitment."
        ),
    },
    "de": {
        "p1": 'Sie kontaktieren die Haartransplantationsklinik "Global Health Istanbul / Dr. Merdan Çelik"',
        "p2": (
            "Einfacher und schneller Prozess:\n\n"
            "1️⃣ Senden Sie uns 6-7 Fotos Ihres Haars (Vorderseite, Seiten, Scheitel und Rückseite) ohne Blitz.\n\n"
            "2️⃣ Teilen Sie uns Ihren vollständigen Namen und Ihre E-Mail-Adresse mit.\n\n"
            "Innerhalb von 24-48 Stunden sendet Ihnen unser medizinisches Team einen detaillierten Bericht.\n\n"
            "📩 Danach beantworten wir gerne alle Ihre Fragen.\n\n"
            "https://trasplantepeloturquia.com/\n\n"
            "Premium: 1.990€ – Alles inklusive (ohne Flüge).\n"
            "Premium +: 2.390€ – Alles inklusive (mit Flügen bis 400€)."
        ),
        "p3": (
            "Bevor Sie sich entscheiden, empfehlen wir Ihnen, die Zertifizierungen des Arztes zu prüfen. "
            "In der Türkei ist die gesetzliche Mindestanforderung ein MD – Tıp Doktoru, "
            "was beim Vergleich von Kliniken nicht immer geprüft wird. Wir helfen Ihnen gerne dabei.\n\n"
            "Bei Fragen stehen wir Ihnen jederzeit zur Verfügung. Danke."
        ),
        "fotos_ok": (
            "Fotos korrekt erhalten. Sie erhalten den Bericht des Arztes innerhalb von 24 Stunden; "
            "wir würden eine Empfangsbestätigung begrüßen. "
            "Für weitere Fragen stehen wir Ihnen zur Verfügung."
        ),
        "pedir_datos": "Wir benötigen außerdem Ihren vollständigen Namen und Ihre E-Mail-Adresse.",
        "informe": (
            "Bericht per WhatsApp und E-Mail gesendet; wir bitten um Bestätigung. "
            "Eingriff durch einen approbierten Arzt (Tıp Doktoru), gesetzliche Anforderung in der Türkei. "
            "Optionen: Premium 1.990€ oder Premium Plus 2.390€. "
            "Wenn Sie einen Anruf vereinbaren möchten, teilen Sie uns dies bitte mit. Danke."
        ),
        "audio_oferta": "🎙️ Möchten Sie eine kurze Sprachnachricht von Dr. Çelik hören? Antworten Sie mit *AUDIO*.",
        "no_interes": "Perfekt! Wir halten Sie über unsere Aktionen auf dem Laufenden 😊\nSchreiben Sie uns jederzeit unverbindlich.",
    },
    "fr": {
        "p1": 'Vous contactez la clinique de transplantation capillaire "Global Health Istanbul / Dr. Merdan Çelik"',
        "p2": (
            "Processus simple et rapide :\n\n"
            "1️⃣ Envoyez-nous 6-7 photos de vos cheveux (devant, côtés, couronne et arrière) sans flash.\n\n"
            "2️⃣ Indiquez-nous votre nom complet et votre adresse e-mail.\n\n"
            "Sous 24-48 heures, notre équipe médicale vous enverra un rapport détaillé.\n\n"
            "📩 Ensuite, nous serons ravis de répondre à toutes vos questions.\n\n"
            "https://trasplantepeloturquia.com/\n\n"
            "Premium : 1 990€ – Tout inclus (sans vols).\n"
            "Premium + : 2 390€ – Tout inclus (avec vols jusqu'à 400€)."
        ),
        "p3": (
            "Avant de décider, nous vous recommandons de vérifier les certifications du médecin. "
            "En Turquie, l'exigence légale minimale est d'être MD – Tıp Doktoru, "
            "ce qui n'est pas toujours vérifié lors de la comparaison des cliniques. Nous pouvons vous aider.\n\n"
            "Pour toute question, n'hésitez pas à nous contacter. Merci."
        ),
        "fotos_ok": (
            "Photos reçues correctement. Vous recevrez le rapport du médecin dans les 24 heures ; "
            "nous vous remercions de confirmer la réception. "
            "Nous restons à votre disposition pour toute question."
        ),
        "pedir_datos": "Nous aurions également besoin de votre nom complet et de votre adresse e-mail.",
        "informe": (
            "Rapport envoyé par WhatsApp et e-mail ; nous vous remercions de confirmer. "
            "Procédure réalisée par un médecin agréé MD (Tıp Doktoru), exigence légale en Turquie. "
            "Options : Premium 1 990€ ou Premium Plus 2 390€. "
            "Si vous souhaitez organiser un appel, merci de nous l'indiquer avec vos dates de voyage."
        ),
        "audio_oferta": "🎙️ Vous souhaitez écouter un court message vocal du Dr. Çelik ? Répondez *AUDIO*.",
        "no_interes": "Parfait ! Nous vous tiendrons informé de nos promotions 😊\nN'hésitez pas à nous écrire sans engagement.",
    },
    "it": {
        "p1": 'Stai contattando la clinica di trapianto di capelli "Global Health Istanbul / Dr. Merdan Çelik"',
        "p2": (
            "Processo semplice e veloce:\n\n"
            "1️⃣ Inviaci 6-7 foto dei tuoi capelli (fronte, lati, corona e parte posteriore) senza flash.\n\n"
            "2️⃣ Indicaci il tuo nome completo e indirizzo e-mail.\n\n"
            "Entro 24-48 ore, il nostro team medico ti invierà un rapporto dettagliato.\n\n"
            "📩 Successivamente, saremo felici di rispondere a qualsiasi domanda.\n\n"
            "https://trasplantepeloturquia.com/\n\n"
            "Premium: 1.990€ – Tutto incluso (senza voli).\n"
            "Premium +: 2.390€ – Tutto incluso (con voli fino a 400€)."
        ),
        "p3": (
            "Prima di decidere, ti consigliamo di verificare le certificazioni del medico che eseguirà "
            "l'intervento. In Turchia, il requisito legale minimo è essere MD – Tıp Doktoru, "
            "cosa che non sempre viene verificata nel confronto tra cliniche. Possiamo aiutarti a farlo.\n\n"
            "Per qualsiasi domanda, non esitare a contattarci. Grazie."
        ),
        "fotos_ok": (
            "Foto ricevute correttamente. Riceverai il rapporto del medico entro 24 ore; "
            "ti saremmo grati per una conferma di ricezione. "
            "Siamo a tua disposizione per qualsiasi domanda."
        ),
        "pedir_datos": "Avremmo bisogno anche del tuo nome completo e del tuo indirizzo e-mail.",
        "informe": (
            "Rapporto inviato via WhatsApp ed e-mail; siamo grati per la conferma. "
            "Procedura eseguita da un medico abilitato MD (Tıp Doktoru), requisito legale in Turchia. "
            "Opzioni: Premium 1.990€ o Premium Plus 2.390€. "
            "Se desideri organizzare una chiamata, faccelo sapere con le date di viaggio. Grazie."
        ),
        "audio_oferta": "🎙️ Vuoi ascoltare un breve messaggio vocale del Dr. Çelik? Rispondi *AUDIO*.",
        "no_interes": "Perfetto! Ti terremo aggiornato sulle nostre promozioni 😊\nScrivici quando vuoi, senza impegno.",
    },
    "pt": {
        "p1": 'Está a contactar a clínica de transplante capilar "Global Health Istanbul / Dr. Merdan Çelik"',
        "p2": (
            "Processo simples e rápido:\n\n"
            "1️⃣ Envie-nos 6-7 fotos do seu cabelo (frente, lados, coroa e parte traseira) sem flash.\n\n"
            "2️⃣ Indique-nos o seu nome completo e endereço de e-mail.\n\n"
            "Em 24-48 horas, a nossa equipa médica enviar-lhe-á um relatório detalhado.\n\n"
            "📩 Depois, teremos todo o prazer em responder a qualquer dúvida.\n\n"
            "https://trasplantepeloturquia.com/\n\n"
            "Premium: 1.990€ – Tudo incluído (sem voos).\n"
            "Premium +: 2.390€ – Tudo incluído (com voos até 400€)."
        ),
        "p3": (
            "Antes de decidir, recomendamos que verifique as certificações do médico que realizará "
            "o procedimento. Na Turquia, o requisito legal mínimo é ser MD – Tıp Doktoru, "
            "algo que nem sempre é verificado ao comparar clínicas. Podemos ajudá-lo a verificar isso.\n\n"
            "Se tiver alguma dúvida, não hesite em contactar-nos. Obrigado."
        ),
        "fotos_ok": (
            "Fotografias recebidas corretamente. Receberá o relatório do médico em 24 horas; "
            "agradecemos confirmação de receção. "
            "Ficamos à sua disposição para qualquer questão."
        ),
        "pedir_datos": "Precisaríamos também do seu nome completo e endereço de e-mail.",
        "informe": (
            "Relatório enviado por WhatsApp e e-mail; agradecemos confirmação. "
            "Procedimento realizado por médico licenciado MD (Tıp Doktoru), requisito legal na Turquia. "
            "Opções: Premium 1.990€ ou Premium Plus 2.390€. "
            "Se precisar de agendar uma chamada, indique-nos juntamente com as datas de viagem. Obrigado."
        ),
        "audio_oferta": "🎙️ Gostarias de ouvir uma breve mensagem de voz do Dr. Çelik? Responde *AUDIO*.",
        "no_interes": "Perfeito! Vamos mantê-lo informado sobre as nossas promoções 😊\nEscreve-nos quando quiseres, sem compromisso.",
    },
}

# Prefijos de país → idioma (fallback)
PREFIX_LANG = {
    "34": "es", "44": "en", "1": "en", "49": "de",
    "33": "fr", "39": "it", "351": "pt", "41": "de",
    "32": "fr", "52": "es", "54": "es", "55": "pt",
    "380": "en",   # Ucrania → inglés (sin plantilla ucraniana)
}

def get_msgs(lang: str) -> dict:
    """Devuelve el dict de mensajes para el idioma (fallback a 'es')."""
    return MSGS.get(lang, MSGS["es"])

# Alias en español para compatibilidad con código existente
MSG_PEDIR_DATOS = MSGS["es"]["pedir_datos"]
MSG_FOTOS_OK    = MSGS["es"]["fotos_ok"]
MSG_INFORME     = MSGS["es"]["informe"]
MSG_P1          = MSGS["es"]["p1"]
MSG_P2          = MSGS["es"]["p2"]
MSG_P3          = MSGS["es"]["p3"]
