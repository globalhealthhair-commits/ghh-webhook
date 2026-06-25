"""
GHH — Sistema automatizado emails pre-llegada clínica.

3 emails por cliente (siempre en inglés):
  - D-2 @ 10:00 Madrid → Liquidaciones completas → globalhealthhair + anastasia
  - D-1 @ 08:00 Madrid → Recordatorio llegada (sin cálculos) → anastasia + sergi + hassullah
  - D-1 @ 10:00 Madrid → Liquidaciones completas (2ª vez) → globalhealthhair + anastasia

Fuente de datos: Google Sheets (Hoja 1) + Drive folder "Contratos Reales"
Envío: SMTP Gmail con App Password
"""

import os, smtplib, traceback, requests
from datetime import datetime, date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Constantes ─────────────────────────────────────────────────────────────────
SHEET_ID       = "1uMECTEaF8DzdpcxnFKTcGELK4GgRrpfeHFr3xbLRFkY"
DRIVE_FOLDER   = "16GEIq84ENlAycvxXI7ps94oUZeYBHn8u"
TO_CLINIC      = "globalhealthhair@gmail.com"
CC_ANASTASIA   = "anastasiia.yevseienko@gmail.com"
TO_SERGI       = "sergimaymo@gmail.com"
TO_HASSULLAH   = "hbayhan5609@gmail.com"
TO_GIORGIA     = "giorgiarocchetto@gmail.com"

# Costes fijos clínica
COST_FUE       = 1350
COST_DHI       = 1400
COST_COMPANION = 60
COST_NIGHT_PAX = 70
COST_NIGHT_COMP= 20
COST_SEDACION  = 150
COST_SHAMPOO   = 250

# Precios cliente
PRICE_DHI_SUPP = 185
PRICE_SEDACION = 190
PRICE_SHAMPOO  = 290


def _cfg(key):
    v = os.environ.get(key)
    if not v:
        raise RuntimeError(f"Variable de entorno faltante: {key}")
    return v


def _get_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id":     _cfg("GOOGLE_CLIENT_ID"),
        "client_secret": _cfg("GOOGLE_CLIENT_SECRET"),
        "refresh_token": _cfg("GOOGLE_REFRESH_TOKEN"),
        "grant_type":    "refresh_token"
    }, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def _send_smtp(to_list, cc_list, subject, body):
    """Envía email via SMTP Gmail con App Password."""
    smtp_user = _cfg("GMAIL_SMTP_USER")
    smtp_pass = _cfg("GMAIL_SMTP_PASS")

    msg = MIMEMultipart()
    msg["From"]    = smtp_user
    msg["To"]      = ", ".join(to_list)
    msg["Cc"]      = ", ".join(cc_list)
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    all_recipients = to_list + cc_list
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(smtp_user, smtp_pass)
        s.sendmail(smtp_user, all_recipients, msg.as_string())
    print(f"[CLINIC EMAIL] Enviado a {all_recipients} | {subject}")


def _parse_date(date_str):
    """Parsea fechas en formato DD/MM/YYYY o D/M/YYYY."""
    date_str = date_str.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%-d/%-m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    # Intento manual para "10/3/2026" → "10/03/2026"
    parts = date_str.split("/")
    if len(parts) == 3:
        d, m, y = parts
        try:
            return date(int(y), int(m), int(d))
        except ValueError:
            pass
    raise ValueError(f"No se pudo parsear la fecha: {date_str}")


def _extract_name(raw):
    """Extrae nombre limpio de 'Will Freddy Mendez (450pp//1990) P+ 2 pax'."""
    if "(" in raw:
        return raw.split("(")[0].strip()
    return raw.strip()


def _get_clients():
    """Lee el spreadsheet y devuelve lista de clientes con sus datos."""
    token = _get_token()
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
           f"/values/Hoja%201!A1:Z100")
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    r.raise_for_status()
    rows = r.json().get("values", [])

    clients = []
    for row in rows[2:]:  # saltar 2 filas de cabecera
        if len(row) < 26:
            row += [""] * (26 - len(row))
        checkin_raw = row[11].strip()  # col L
        if not checkin_raw:
            continue
        try:
            checkin = _parse_date(checkin_raw)
        except ValueError:
            continue

        try:
            clinic_payment = float(row[25].replace(".", "").replace(",", ".").replace("€", "").strip())
        except (ValueError, IndexError):
            continue

        try:
            cost_hair = int(row[23].strip()) if row[23].strip() else 0
        except ValueError:
            cost_hair = 0

        try:
            extra_nights = int(row[19].strip()) if row[19].strip() else 0
        except ValueError:
            extra_nights = 0

        try:
            pax = int(row[3].strip()) if row[3].strip() else 1
        except ValueError:
            pax = 1

        clients.append({
            "name":            _extract_name(row[1]),
            "contract_type":   row[2].strip(),
            "pax":             pax,
            "airline":         row[7].strip(),
            "flight_out":      row[8].strip(),
            "arrival_time":    row[9].strip(),
            "airport":         row[10].strip(),
            "checkin":         checkin,
            "checkout_raw":    row[12].strip(),
            "cost_hair":       cost_hair,
            "extra_nights":    extra_nights,
            "clinic_payment":  clinic_payment,
        })
    return clients


def _contract_exists(client_name, token):
    """Comprueba si existe un contrato en Drive para este cliente."""
    # Busca archivo cuyo nombre contenga el primer apellido del cliente
    words = client_name.split()
    search_term = words[1] if len(words) > 1 else words[0]

    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": (f"'{DRIVE_FOLDER}' in parents and trashed=false "
              f"and name contains '{search_term}'"),
        "fields": "files(id,name)"
    }
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=10)
        files = r.json().get("files", [])
        return len(files) > 0
    except Exception:
        return False


def _calc_base_deductions(client):
    """Calcula deducciones fijas siempre presentes (pre-pagadas en España)."""
    deductions = {}
    cost_hair   = client["cost_hair"]
    pax         = client["pax"]
    extra       = client["extra_nights"]

    # Si DHI pre-pagado en España (cost_hair = 1400), la clínica siempre deduce DHI
    if cost_hair == COST_DHI:
        deductions["DHI COST"] = -COST_DHI
    else:
        deductions["CLINIC COST"] = -COST_FUE

    # Acompañante si 2 pax
    if pax >= 2:
        deductions["2 PAX"] = -COST_COMPANION

    # Noches extra
    if extra > 0:
        deductions[f"EXTRA NIGHT (PAX)"] = -(COST_NIGHT_PAX * extra)
        if pax >= 2:
            deductions[f"EXTRA NIGHT (COMP)"] = -(COST_NIGHT_COMP * extra)

    return deductions


def _fmt_scenario(title, contract_income, extras_in, base_deduc):
    """Formatea un bloque de escenario."""
    lines = [title, ""]
    total_in = contract_income + sum(extras_in.values())
    total_out = sum(base_deduc.values())
    total = total_in + total_out

    lines.append(f"CONTRACT            +{int(contract_income):,}€".replace(",", "."))
    for label, amt in extras_in.items():
        lines.append(f"{label:<20}+{int(amt):,}€".replace(",", "."))
    lines.append("                    ───────")
    for label, amt in base_deduc.items():
        lines.append(f"{label:<20}{int(amt):,}€".replace(",", "."))
    lines.append("                    ───────")
    sign = "+" if total >= 0 else ""
    lines.append(f"TOTAL GHH:           {sign}{int(total):,}€".replace(",", "."))
    return "\n".join(lines)


def _build_liquidation_body(client):
    """Construye el cuerpo del email de liquidaciones."""
    cp       = client["clinic_payment"]
    ch       = client["cost_hair"]
    pax      = client["pax"]
    extra    = client["extra_nights"]
    base_ded = _calc_base_deductions(client)

    # ─── Línea de cabecera pre-pagado España ───
    prepaid_items = []
    if ch == COST_DHI:
        prepaid_items.append("DHI")
    if pax >= 2:
        prepaid_items.append("Companion")
    if extra > 0:
        prepaid_items.append(f"{extra} Extra Night{'s' if extra > 1 else ''}")
    prepaid_str = " · ".join(prepaid_items) if prepaid_items else "—"

    header = (
        f"CLIENT: {client['name']} | {pax} Pax\n"
        f"CHECK-IN: {client['checkin'].strftime('%d/%m/%Y')} | CHECK-OUT: {client['checkout_raw']}\n"
        f"FLIGHT: {client['airline']} {client['flight_out']} — {client['arrival_time']}h | Airport: {client['airport']}\n"
        f"CONTRACT AMOUNT (clinic payment): {int(cp):,}€\n".replace(",", ".")
        + (f"PRE-PAID IN SPAIN: {prepaid_str}\n" if prepaid_items else "")
        + "────────────────────────────────────────"
    )

    scenarios = []

    if ch == COST_DHI:
        # DHI pre-pagado — mostrar: ONLY FUE ZAFIRO / DHI / DHI+SED / DHI+SHAMPOO / DHI+SED+SHAMPOO
        fue_ded = dict(base_ded)
        fue_ded["CLINIC COST"] = -COST_FUE
        del fue_ded["DHI COST"]
        scenarios.append(_fmt_scenario("ONLY FUE ZAFIRO", cp, {}, fue_ded))

        scenarios.append(_fmt_scenario("DHI", cp, {}, base_ded))

        ded_sed = dict(base_ded)
        scenarios.append(_fmt_scenario("DHI + SEDATION", cp,
            {"SEDATION": PRICE_SEDACION},
            {**ded_sed, "SEDATION": -COST_SEDACION}))

        ded_sh = dict(base_ded)
        scenarios.append(_fmt_scenario("DHI + SHAMPOO", cp,
            {"SHAMPOO": PRICE_SHAMPOO},
            {**ded_sh, "SHAMPOO": -COST_SHAMPOO}))

        ded_all = dict(base_ded)
        scenarios.append(_fmt_scenario("DHI + SEDATION + SHAMPOO", cp,
            {"SEDATION": PRICE_SEDACION, "SHAMPOO": PRICE_SHAMPOO},
            {**ded_all, "SEDATION": -COST_SEDACION, "SHAMPOO": -COST_SHAMPOO}))

    else:
        # FUE base — mostrar: ONLY FUE / FUE+SED / DHI / DHI+SED
        scenarios.append(_fmt_scenario("ONLY FUE ZAFIRO", cp, {}, base_ded))

        ded_sed = dict(base_ded)
        scenarios.append(_fmt_scenario("FUE + SEDATION", cp,
            {"SEDATION": PRICE_SEDACION},
            {**ded_sed, "SEDATION": -COST_SEDACION}))

        dhi_ded = dict(base_ded)
        dhi_ded["CLINIC COST"] = -COST_DHI
        scenarios.append(_fmt_scenario("DHI", cp,
            {"DHI SUPPLEMENT": PRICE_DHI_SUPP},
            dhi_ded))

        dhi_ded2 = dict(dhi_ded)
        scenarios.append(_fmt_scenario("DHI + SEDATION", cp,
            {"DHI SUPPLEMENT": PRICE_DHI_SUPP, "SEDATION": PRICE_SEDACION},
            {**dhi_ded2, "SEDATION": -COST_SEDACION}))

    separator = "\n\n════════════════════════════════════════\n\n"
    footer = "\n\nGlobal Health Hair Istanbul\nglobalhealthhair@gmail.com | +34 648 423 777"

    return header + "\n\n" + separator.join(scenarios) + footer


def _build_reminder_body(client):
    """Construye el cuerpo del email de recordatorio (sin cálculos)."""
    checkin_fmt  = client["checkin"].strftime("%d/%m/%Y")
    checkout_fmt = client["checkout_raw"]
    return (
        f"ARRIVAL REMINDER — {checkin_fmt}\n\n"
        f"Client {client['name']} arrives TOMORROW.\n\n"
        f"────────────────────────────────────────\n"
        f"CLIENT:     {client['name']}\n"
        f"CHECK-IN:   {checkin_fmt}\n"
        f"CHECK-OUT:  {checkout_fmt}\n"
        f"PAX:        {client['pax']}\n\n"
        f"FLIGHT INFO:\n"
        f"  Airline:  {client['airline']}\n"
        f"  Flight:   {client['flight_out']}\n"
        f"  Time:     {client['arrival_time']}h\n"
        f"  Airport:  {client['airport']}\n"
        f"────────────────────────────────────────\n\n"
        f"ACTION REQUIRED TODAY:\n\n"
        f"Please contact the client via WhatsApp TODAY to:\n\n"
        f"  1. Explain the clinic reception procedure and what\n"
        f"     to expect upon arrival at the airport.\n\n"
        f"  2. Send the airport departure videos with all\n"
        f"     relevant information about the exit process.\n\n"
        f"  3. Share any additional travel tips that may be\n"
        f"     useful for their trip (hotel check-in, transport,\n"
        f"     local contacts, etc.).\n\n"
        f"Please ensure all coordination is completed today\n"
        f"so the client arrives fully informed and prepared.\n\n"
        f"────────────────────────────────────────\n"
        f"Global Health Hair Istanbul\n"
        f"globalhealthhair@gmail.com | +34 648 423 777"
    )


def _build_missing_contract_body(client):
    """Email de aviso urgente para Anastasia cuando falta el contrato."""
    return (
        f"URGENT — CONTRACT MISSING\n\n"
        f"The financial summary email for the following client CANNOT be sent "
        f"because the signed contract has NOT been uploaded to the "
        f"'Contratos Reales' folder in Google Drive.\n\n"
        f"CLIENT:    {client['name']}\n"
        f"CHECK-IN:  {client['checkin'].strftime('%d/%m/%Y')}\n"
        f"FLIGHT:    {client['airline']} {client['flight_out']} — "
        f"{client['arrival_time']}h ({client['airport']})\n\n"
        f"ACTION REQUIRED: Please upload the signed contract to:\n"
        f"https://drive.google.com/drive/folders/16GEIq84ENlAycvxXI7ps94oUZeYBHn8u\n\n"
        f"Global Health Hair Istanbul\n"
        f"globalhealthhair@gmail.com | +34 648 423 777"
    )


def run_clinic_liquidation_emails():
    """
    Job para las 10:00h Madrid (09:00 Atlantic/Canary).
    Envía email de liquidaciones a clientes que llegan en 1 ó 2 días.
    """
    today = date.today()
    print(f"[CLINIC LIQUIDATION] Comprobando clientes para {today}")

    try:
        token = _get_token()
        clients = _get_clients()
    except Exception as e:
        print(f"[CLINIC LIQUIDATION] Error obteniendo datos: {e}")
        return

    for client in clients:
        days_until = (client["checkin"] - today).days
        if days_until not in (1, 2):
            continue

        name = client["name"]
        checkin_str = client["checkin"].strftime("%d/%m/%Y")
        label = f"D-{days_until}"

        contract_ok = _contract_exists(name, token)

        if contract_ok:
            subject = (f"PRE-ARRIVAL CLINIC SUMMARY ({label}) — "
                       f"{name} | {checkin_str}")
            body = _build_liquidation_body(client)
            try:
                _send_smtp([TO_CLINIC], [CC_ANASTASIA], subject, body)
                print(f"[CLINIC LIQUIDATION] ✅ Enviado {label} para {name}")
            except Exception as e:
                print(f"[CLINIC LIQUIDATION] ❌ Error enviando para {name}: {e}")
                traceback.print_exc()
        else:
            # Contrato no encontrado → aviso urgente a Anastasia
            subject = (f"⚠️ URGENT — Contract missing for {name} | {checkin_str}")
            body = _build_missing_contract_body(client)
            try:
                _send_smtp([CC_ANASTASIA], [], subject, body)
                print(f"[CLINIC LIQUIDATION] ⚠️ Contrato faltante notificado para {name}")
            except Exception as e:
                print(f"[CLINIC LIQUIDATION] ❌ Error enviando aviso para {name}: {e}")


def run_clinic_reminder_emails():
    """
    Job para las 08:00h Madrid (07:00 Atlantic/Canary).
    Envía recordatorio de llegada para clientes que llegan MAÑANA.
    Destinatarios: Anastasia + Sergi + Hassullah (sin datos financieros).
    """
    today = date.today()
    print(f"[CLINIC REMINDER] Comprobando clientes para {today}")

    try:
        clients = _get_clients()
    except Exception as e:
        print(f"[CLINIC REMINDER] Error obteniendo datos: {e}")
        return

    for client in clients:
        days_until = (client["checkin"] - today).days
        if days_until != 1:
            continue

        name = client["name"]
        checkin_str = client["checkin"].strftime("%d/%m/%Y")
        subject = f"ARRIVAL TOMORROW — {name} | {checkin_str}"
        body = _build_reminder_body(client)

        try:
            _send_smtp(
                [CC_ANASTASIA, TO_SERGI, TO_HASSULLAH, TO_GIORGIA],
                [],
                subject,
                body
            )
            print(f"[CLINIC REMINDER] ✅ Recordatorio enviado para {name}")
        except Exception as e:
            print(f"[CLINIC REMINDER] ❌ Error enviando recordatorio para {name}: {e}")
            traceback.print_exc()
