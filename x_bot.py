"""
x_bot.py — Bot X/Twitter automático para Global Health Hair
Publica 1-2 tweets/día optimizados para conversión y posicionamiento SEO.
Anti-penalización: variedad de contenido, delays aleatorios, sin spam.

Auth: OAuth2 User Context (bearer token user-level). Actualizado 2026-06-29.
"""

import os, json, random, time, hashlib, urllib.request
from datetime import datetime, timedelta

# ── Credenciales ─────────────────────────────────────────────────────────────
def _get_oauth2_token():
    """Lee el OAuth2 User Access Token. Railway env var o meta_tokens.json."""
    token = os.environ.get("X_OAUTH2_USER_TOKEN")
    if not token:
        base = os.path.dirname(os.path.abspath(__file__))
        creds_path = os.path.join(base, "../credentials/meta_tokens.json")
        creds = json.load(open(creds_path))
        token = creds["x_ghh_social_bot"]["oauth2_user_access_token"]
    return token

def _post_tweet(text):
    """Publica un tweet via X API v2 con OAuth2 User Context. Retorna tweet_id o None."""
    token = _get_oauth2_token()
    payload = json.dumps({"text": text}).encode()
    req = urllib.request.Request(
        "https://api.twitter.com/2/tweets",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
            return data.get("data", {}).get("id")
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"[x_bot] POST /tweets error {e.code}: {err[:200]}")
        return None

def _get_x_client():
    """Compatibilidad: devuelve None (ya no usamos Tweepy OAuth1)."""
    return None

# ── Banco de tweets (30+ variaciones, anti-duplicado) ───────────────────────
# Formato: (texto, categoría, hashtags)
# Twitter cuenta URL como 23 chars. Límite efectivo texto+hashtags = 257 chars.

TWEET_BANK = [
    # --- DIFERENCIADOR MÉDICO (máxima conversión) ---
    {
        "text": "¿Sabías que en la mayoría de clínicas turcas quien opera NO es médico? El Dr. Merdan Çelik MD realiza personalmente cada trasplante en Global Health Hair. +22 años · +20.000 pacientes. Consulta gratis 👉 {url}",
        "tags": "#trasplantecapilar #calvicie #injertocapilar",
        "category": "diferenciador",
        "weight": 3
    },
    {
        "text": "En Turquía, la mayoría de trasplantes los realiza un técnico, no un médico. En Global Health Hair, el Dr. Merdan Çelik MD opera cada intervención. +20.000 pacientes. Análisis gratis 👉 {url}",
        "tags": "#trasplantecapilar #alopecia #injertopelo",
        "category": "diferenciador",
        "weight": 3
    },
    {
        "text": "Antes de elegir clínica en Turquía, pregunta: ¿quién opera exactamente? ¿Tiene título médico? En Global Health Hair, el Dr. Çelik MD entra al quirófano. Siempre. Consulta sin compromiso 👉 {url}",
        "tags": "#trasplantecapilar #calvicie #estambul",
        "category": "diferenciador",
        "weight": 2
    },
    # --- PRECIO / COMPARATIVA ---
    {
        "text": "Trasplante capilar FUE en España: 5.000-7.000€. En Global Health Hair (Estambul): desde 1.990€ todo incluido + médico licenciado. El ahorro y la calidad no tienen por qué estar reñidos. {url}",
        "tags": "#trasplantecapilar #injertocapilar #alopecia",
        "category": "precio",
        "weight": 2
    },
    {
        "text": "✅ Hotel 5* incluido\n✅ Traslados incluidos\n✅ Análisis preoperatorios\n✅ Médico licenciado (no técnico)\n\nTodo desde 1.990€. Trasplante capilar en Estambul con Global Health Hair 👉 {url}",
        "tags": "#trasplantecapilar #calvicie #globalhealthhair",
        "category": "precio",
        "weight": 2
    },
    {
        "text": "En UK pagan +£9.000 por un trasplante capilar. En Global Health Hair operan con médico licenciado desde 1.990€. La diferencia: 7.000€ en el bolsillo. Consulta gratis 👉 {url}",
        "tags": "#hairtransplant #trasplantecapilar #calvicie",
        "category": "precio",
        "weight": 2
    },
    # --- EDUCATIVO / SEO ---
    {
        "text": "¿Cuántos injertos necesitas? Norwood 2-3 → 1.500-2.500 injertos. Norwood 4 → 2.500-3.200. Norwood 5-6 → 3.000-4.000. Calcula el tuyo gratis 👉 {url}",
        "tags": "#trasplantecapilar #alopecia #norwood #calvicie",
        "category": "educativo",
        "weight": 2
    },
    {
        "text": "Técnica FUE vs DHI: ¿cuál es mejor para ti?\n\nFUE → rasurado completo, mayor zona a cubrir\nDHI → sin rasurar, máxima densidad\n\nEl Dr. Çelik elige la mejor para cada caso. Consulta gratis 👉 {url}",
        "tags": "#FUE #DHI #trasplantecapilar #injertocapilar",
        "category": "educativo",
        "weight": 2
    },
    {
        "text": "El 'shock loss' asusta pero es normal. A las 8 semanas el pelo trasplantado cae... y vuelve a crecer. El resultado definitivo: a los 12 meses. Guía completa del proceso paso a paso 👉 {url}",
        "tags": "#trasplantecapilar #shockloss #recuperacion #calvicie",
        "category": "educativo",
        "weight": 2
    },
    {
        "text": "3 preguntas que debes hacer ANTES de elegir clínica de trasplante capilar en Turquía:\n\n1️⃣ ¿Quién opera exactamente?\n2️⃣ ¿Tiene licencia médica?\n3️⃣ ¿Cuántas operaciones ha realizado?\n\n👉 {url}",
        "tags": "#trasplantecapilar #alopecia #estambul",
        "category": "educativo",
        "weight": 2
    },
    {
        "text": "Alopecia androgenética: afecta al 44% de los hombres españoles. Tratamientos: minoxidil, finasteride, trasplante. El trasplante es la única solución permanente. Consulta sin compromiso 👉 {url}",
        "tags": "#alopecia #calvicie #trasplantecapilar #pelo",
        "category": "educativo",
        "weight": 1
    },
    # --- CONFIANZA / CREDENCIALES ---
    {
        "text": "El Dr. Merdan Çelik:\n🎓 Médico licenciado (MD, Universidad de Trakya, 1997)\n⏱️ +22 años operando trasplantes capilares\n👤 +20.000 pacientes tratados\n🏥 Estambul, Turquía\n\nConsulta gratis 👉 {url}",
        "tags": "#trasplantecapilar #DrCelik #globalhealthhair",
        "category": "credenciales",
        "weight": 2
    },
    {
        "text": "+20.000 pacientes han confiado en el Dr. Merdan Çelik MD para su trasplante capilar. 22 años de experiencia. Consulta gratuita con análisis personalizado. Sin compromiso 👉 {url}",
        "tags": "#trasplantecapilar #calvicie #injertocapilar #estambul",
        "category": "credenciales",
        "weight": 2
    },
    {
        "text": "Global Health Hair, Estambul:\n✅ Médico licenciado en quirófano\n✅ +20.000 pacientes\n✅ +22 años de experiencia\n✅ Precio desde 1.990€ todo incluido\n✅ Atención en español\n\n👉 {url}",
        "tags": "#trasplantecapilar #injertocapilar #globalhealthhair",
        "category": "credenciales",
        "weight": 2
    },
    # --- TESTIMONIOS / SOCIAL PROOF ---
    {
        "text": "¿Cuánto tiempo tarda en verse el resultado? Mes 3: primeros pelillos. Mes 6: densidad visible. Mes 12: resultado definitivo. La paciencia es parte del tratamiento 💪 Más info 👉 {url}",
        "tags": "#trasplantecapilar #resultado #antes #despues",
        "category": "proceso",
        "weight": 1
    },
    {
        "text": "El viaje de trasplante capilar en Estambul:\n✈️ Llegada — recogida en aeropuerto\n🏥 Día 1 — operación con Dr. Çelik MD\n🏨 Día 2 — revisión + hotel incluido\n✈️ Día 3 — vuelta a casa\n\nDesde 1.990€ 👉 {url}",
        "tags": "#trasplantecapilar #estambul #turismo #calvicie",
        "category": "proceso",
        "weight": 2
    },
    # --- BARBA / NICHOS ---
    {
        "text": "¿Barba escasa o con huecos? El trasplante de barba con DHI rellena los huecos de forma natural. Sin rasurado visible durante el proceso. Desde 1.990€ en Estambul 👉 {url}",
        "tags": "#trasplantebarba #barba #DHI #estambul",
        "category": "barba",
        "weight": 1
    },
    {
        "text": "Trasplante capilar para mujer: la técnica DHI permite operarse SIN rasurar completamente el cabello. Resultados naturales y permanentes. Consulta personalizada gratis 👉 {url}",
        "tags": "#trasplantecapilar #mujer #alopecia #DHI",
        "category": "femenino",
        "weight": 1
    },
    # --- ESTAMBUL / TURISMO MÉDICO ---
    {
        "text": "500.000 europeos viajan a Turquía cada año para trasplante capilar. ¿Por qué? Ahorro del 60-70%, mismo estándar médico, médico licenciado en Global Health Hair. Análisis gratis 👉 {url}",
        "tags": "#trasplantecapilar #turquía #turismo #estambul",
        "category": "turismo",
        "weight": 1
    },
    {
        "text": "¿Vale la pena el trasplante capilar en Turquía? El ahorro vs España: 3.000-5.000€. El vuelo: 150-250€ r/t. Médico licenciado incluido. La respuesta es sí, si eliges bien la clínica 👉 {url}",
        "tags": "#trasplantecapilar #turquía #precio #calvicie",
        "category": "turismo",
        "weight": 1
    },
]

# ── Historial de tweets publicados (anti-duplicado) ──────────────────────────
def _get_history_file():
    base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.environ.get("DATA_DIR", os.path.join(base, "data"))
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "x_tweet_history.json")

def _load_history():
    f = _get_history_file()
    if os.path.exists(f):
        return json.load(open(f))
    return {"published": [], "last_tweet_at": None}

def _save_history(h):
    json.dump(h, open(_get_history_file(), "w"), indent=2)

def _tweet_hash(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]

# ── Selección de tweet (pesos + anti-duplicado 14 días) ─────────────────────
def _pick_tweet():
    history = _load_history()
    recent_hashes = {e["hash"] for e in history["published"][-30:]}

    # Expandir banco según pesos
    pool = []
    for t in TWEET_BANK:
        h = _tweet_hash(t["text"])
        if h not in recent_hashes:
            pool.extend([t] * t.get("weight", 1))

    if not pool:
        # Todos usados recientemente → reiniciar (permite reciclar después de 30 tweets)
        pool = TWEET_BANK.copy()

    return random.choice(pool)

# ── Construcción del texto final ─────────────────────────────────────────────
URL = "https://trasplantepeloturquia.com"

def _build_tweet(template):
    """Construye el texto final y verifica longitud (Twitter: URL=23 chars)."""
    text = template["text"].format(url=URL)
    tags = template.get("tags", "")

    full = f"{text} {tags}".strip() if tags else text

    # Calcular longitud efectiva Twitter (URL = 23 chars independiente de longitud real)
    url_real_len = len(URL)
    effective = len(full) - (url_real_len - 23)

    if effective > 280:
        # Recortar hashtags si es necesario
        full = text.strip()
        effective = len(full) - (url_real_len - 23)

    return full, effective

# ── Publicar tweet ────────────────────────────────────────────────────────────
def post_tweet(dry_run=False):
    """
    Selecciona y publica un tweet optimizado.
    dry_run=True → solo muestra el tweet sin publicar (para tests).
    Devuelve dict con resultado.
    """
    template = _pick_tweet()
    text, effective_len = _build_tweet(template)

    result = {
        "category": template["category"],
        "text": text,
        "effective_chars": effective_len,
        "dry_run": dry_run,
        "tweet_id": None,
        "url": None,
        "error": None
    }

    if dry_run:
        print(f"[DRY RUN] Tweet ({effective_len} chars):\n{text}")
        return result

    try:
        tweet_id = _post_tweet(text)
        if not tweet_id:
            result["error"] = "API returned no tweet_id (posible rate limit o permisos)"
            return result

        result["tweet_id"] = tweet_id
        result["url"] = f"https://x.com/GlobalHealth69/status/{tweet_id}"

        # Guardar en historial
        history = _load_history()
        history["published"].append({
            "hash": _tweet_hash(template["text"]),
            "tweet_id": tweet_id,
            "category": template["category"],
            "published_at": datetime.utcnow().isoformat(),
            "text_preview": text[:80]
        })
        history["last_tweet_at"] = datetime.utcnow().isoformat()
        history["published"] = history["published"][-60:]
        _save_history(history)

        print(f"✅ Tweet publicado! ID: {tweet_id}")
        print(f"   URL: {result['url']}")
        print(f"   Categoría: {template['category']} | {effective_len} chars")
        return result

    except Exception as e:
        result["error"] = str(e)
        print(f"❌ Error publicando tweet: {e}")
        return result

# ── Lógica de horario óptimo ─────────────────────────────────────────────────
OPTIMAL_HOURS_UTC = [7, 12, 17, 20]  # 07:00, 12:00, 17:00, 20:00 UTC (España = +1/+2h)
TWEETS_PER_DAY = 2  # Máximo para no penalizar

def should_post_now():
    """
    Devuelve True si es buen momento para publicar.
    Lógica: máx 2 tweets/día, solo en horas óptimas (±30 min), mínimo 4h entre tweets.
    """
    history = _load_history()
    now = datetime.utcnow()
    current_hour = now.hour

    # ¿Estamos en una ventana de hora óptima? (±30 min de la hora exacta)
    in_window = any(
        abs(current_hour - h) <= 0 or (current_hour == h - 1 and now.minute >= 30) or (current_hour == h and now.minute <= 30)
        for h in OPTIMAL_HOURS_UTC
    )
    if not in_window:
        return False

    # ¿Cuántos tweets hoy?
    today = now.date().isoformat()
    tweets_today = sum(
        1 for e in history["published"]
        if e.get("published_at", "")[:10] == today
    )
    if tweets_today >= TWEETS_PER_DAY:
        return False

    # ¿Han pasado al menos 4 horas desde el último tweet?
    if history.get("last_tweet_at"):
        last = datetime.fromisoformat(history["last_tweet_at"])
        if (now - last).total_seconds() < 4 * 3600:
            return False

    return True

# ── Función principal para el scheduler de Railway ───────────────────────────
def run_x_bot_cycle():
    """
    Llamar desde scheduler.py o run.py cada 30 minutos.
    Publica solo si es el momento correcto.
    """
    if should_post_now():
        print(f"[X BOT] {datetime.utcnow().isoformat()} — Publicando tweet...")
        result = post_tweet(dry_run=False)
        return result
    else:
        print(f"[X BOT] {datetime.utcnow().isoformat()} — Fuera de ventana, skip.")
        return None

# ── Test local ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if "--dry-run" in sys.argv:
        for i in range(5):
            t = _pick_tweet()
            text, eff = _build_tweet(t)
            print(f"\n--- Tweet {i+1} [{t['category']}] ({eff} chars) ---")
            print(text)
    elif "--post" in sys.argv:
        result = post_tweet(dry_run=False)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Uso: python x_bot.py --dry-run | --post")
