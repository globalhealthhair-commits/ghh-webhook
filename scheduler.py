"""
Capa 1 — Scheduler persistente.
Guarda las acciones pendientes en disco (pending_actions.json).
Si el servidor se cae y reinicia, recupera y reprograma todos los timers.
"""
import json, os, time, threading
from datetime import datetime

_BASE    = os.path.dirname(os.path.abspath(__file__))
_lock    = threading.Lock()
_timers  = {}   # (phone, action) → threading.Timer activo


def _file():
    import config
    return config.PENDING_FILE

def _load():
    f = _file()
    if os.path.exists(f):
        return json.load(open(f))
    return {}

def _save(data):
    json.dump(data, open(_file(), "w"), indent=2, ensure_ascii=False)


def schedule(phone: str, action: str, fire_at: float, **kwargs):
    """Programa una acción y la persiste en disco."""
    with _lock:
        data = _load()
        data.setdefault(phone, {})[action] = {"fire_at": fire_at, **kwargs}
        _save(data)
    _arm(phone, action, fire_at, kwargs)


def cancel(phone: str, action: str):
    """Cancela una acción pendiente."""
    with _lock:
        data = _load()
        if phone in data and action in data[phone]:
            del data[phone][action]
            if not data[phone]:
                del data[phone]
            _save(data)
    key = (phone, action)
    if key in _timers:
        _timers[key].cancel()
        del _timers[key]


def _arm(phone: str, action: str, fire_at: float, kwargs: dict):
    """Crea el threading.Timer real para una acción."""
    delay = max(0, fire_at - time.time())
    key   = (phone, action)

    if key in _timers:
        _timers[key].cancel()

    def run():
        _execute(phone, action, kwargs)

    t = threading.Timer(delay, run)
    t.daemon = True
    t.start()
    _timers[key] = t
    print(f"[SCHED] {action} para {phone} en {datetime.fromtimestamp(fire_at).strftime('%d/%m %H:%M')}")


def _execute(phone: str, action: str, kwargs: dict):
    """Ejecuta la acción y la elimina del disco."""
    with _lock:
        data = _load()
        if phone in data and action in data[phone]:
            del data[phone][action]
            if not data[phone]:
                del data[phone]
            _save(data)

    # Importación tardía para evitar importación circular
    import wa_api, config
    from informe_generator import generate_informe

    try:
        if action == "fotos_ok":
            from webhook_server import load_state
            lang = load_state().get(phone, {}).get("idioma", "es")
            wa_api.send_text(phone, config.get_msgs(lang)["fotos_ok"])
            print(f"[SCHED] fotos_ok enviado a {phone} (idioma: {lang})")

        elif action == "pedir_datos":
            from webhook_server import load_state
            lead = load_state().get(phone, {})
            lang = lead.get("idioma", "es")
            if not lead.get("nombre") or not lead.get("email"):
                wa_api.send_text(phone, config.get_msgs(lang)["pedir_datos"])
                print(f"[SCHED] pedir_datos enviado a {phone} (idioma: {lang})")

        elif action == "informe_diferido":
            from webhook_server import load_state, save_state, _enviar_por_email
            nombre   = kwargs.get("nombre", "")
            foliculos = kwargs.get("foliculos", "")
            tecnica  = kwargs.get("tecnica", "DHI")
            primer   = nombre.split()[0] if nombre else "Diagnostic"
            label    = nombre if nombre else "(sin nombre)"

            state = load_state()
            lang  = state.get(phone, {}).get("idioma", "es")
            m     = config.get_msgs(lang)

            pdf_path = generate_informe(nombre, foliculos, tecnica)
            media_id = wa_api.upload_media(pdf_path, "application/pdf")
            wa_api.send_document(phone, media_id,
                f"Report_GHH_{primer}.pdf",
                f"{foliculos} follicles")
            import time as t; t.sleep(1.5)
            wa_api.send_text(phone, m["informe"])

            lead  = state.get(phone, {})
            email = lead.get("email", "")
            if email:
                _enviar_por_email(email, nombre, pdf_path)

            wa_api.send_text(config.ADMIN_NUMBER,
                f"✅ *Informe enviado* (programado)\n"
                f"👤 {label} · {phone}\n"
                f"📧 Email: {email if email else '— no disponible'}")

            lead.update({"estado": "informe_enviado", "foliculos": foliculos,
                         "tecnica": tecnica, "nombre": nombre})
            state[phone] = lead
            save_state(state)

    except Exception as e:
        import wa_api as _wa, config as _cfg
        _wa.send_text(_cfg.ADMIN_NUMBER, f"❌ Error scheduler ({action} · {phone}): {e}")
        print(f"[SCHED ERROR] {action} {phone}: {e}")


def recover():
    """
    Llamar al arrancar el servidor.
    Reprograma todas las acciones pendientes que sobrevivieron al reinicio.
    """
    data = _load()
    now  = time.time()
    recovered = 0
    for phone, actions in data.items():
        for action, meta in actions.items():
            fire_at = meta.get("fire_at", now)
            kwargs  = {k: v for k, v in meta.items() if k != "fire_at"}
            if fire_at < now:
                # Ya debería haber disparado — ejecutar inmediatamente
                fire_at = now + 5
            _arm(phone, action, fire_at, kwargs)
            recovered += 1
    if recovered:
        print(f"[SCHED] {recovered} acción(es) recuperada(s) tras reinicio")
