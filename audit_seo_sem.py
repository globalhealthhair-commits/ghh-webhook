"""
audit_seo_sem.py — Auditoría diaria completa GHH (SEO + SEM)
07:00 Atlantic/Canary desde Railway (Mac puede estar apagado).

🟢 Ejecuta solo: negativos Ads, pausar DISAPPROVED, mejorar RSA,
                  reescribir metas débiles, IndexNow, alertas 404/CWV.
🔴 Solo reporta:  caídas de posición top pages, gasto sin conversión,
                  dayparting ineficiente, ad spend > umbral sin conv.
"""

import os, requests, traceback, re, base64
from datetime import date, timedelta
from urllib.parse import quote as url_quote

SITE     = "https://trasplantepeloturquia.com"
ADS_VER  = "v21"
GSC_SITE = f"{SITE}/"

# ── RSA Bank (GHH) ───────────────────────────────────────────────────
RSA_HEADLINES = [
    "Médico Licenciado MD",
    "Dr. Çelik +22 Años",
    "FUE Zafiro Estambul",
    "DHI Sin Rasurar Turquía",
    "Trasplante Todo Incluido",
    "Clínica Privada Estambul",
    "Consulta Gratuita Online",
    "Resultados Naturales Reales",
    "Precio Desde 1.990€",
    "Vuelos Incluidos Premium+",
    "Sin Rasurar con DHI",
    "Garantía Médica Turquía",
]
RSA_DESCRIPTIONS = [
    "Trasplante capilar con médico licenciado MD en Estambul. No técnicos. Dr. Çelik.",
    "FUE Zafiro y DHI. +22 años experiencia. Todo incluido desde 1.990€. Consulta gratis.",
    "Clínica privada Estambul. Traslados, hotel y seguimiento incluidos. Dr. Çelik MD.",
]

_MONEY_QUERIES = [
    "trasplante capilar turquia","trasplante pelo turquia",
    "trasplante capilar estambul","trasplante capilar precio",
    "fue zafiro turquia","dhi turquia","injerto capilar turquia",
]
_GEO_TERMS        = {"turquia","turquía","estambul","istanbul","turkey"}
_COMPETITOR_TERMS = {
    "hairturkey","wom clinic","cosmedica","vera clinic","smile hair","estenove",
    "longevita","dr cinik","dr yaman","dr koray","dr levent","dr tayfun",
    "dr umut","dr bayer","dr serkan","clinicana","hair of istanbul"
}
_IRRELEVANT = {"gratis","free","casero","champú","shampoo","vitamina","dieta"}


# ── Helpers ──────────────────────────────────────────────────────────

def _cfg(key):
    v = os.environ.get(key)
    if not v:
        raise RuntimeError(f"Env var faltante: {key}")
    return v

def _cfg_soft(key):
    """Devuelve None en lugar de lanzar si la var no está."""
    return os.environ.get(key)

def _get_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id":     _cfg("GOOGLE_CLIENT_ID"),
        "client_secret": _cfg("GOOGLE_CLIENT_SECRET"),
        "refresh_token": _cfg("GOOGLE_REFRESH_TOKEN"),
        "grant_type":    "refresh_token"
    }, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]

def _send_telegram(msg):
    try:
        token = _cfg_soft("TG_BOT_TOKEN") or _cfg("TG_TOKEN")
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": _cfg("TG_CHAT_ID"), "text": msg[:4000], "parse_mode": "Markdown"},
            timeout=10
        )
    except Exception as e:
        print(f"[AUDIT] Telegram error: {e}")

def _gaql(token, query):
    cid = _cfg("ADS_CUSTOMER_ID")
    r = requests.post(
        f"https://googleads.googleapis.com/v21/customers/{cid}/googleAds:search",
        headers={
            "Authorization":   f"Bearer {token}",
            "developer-token": _cfg("ADS_DEV_TOKEN"),
            "Content-Type":    "application/json"
        },
        json={"query": query}, timeout=20
    )
    if not r.ok:
        print(f"[AUDIT] Ads GAQL error {r.status_code}: {r.text[:120]}")
        return []
    return r.json().get("results", [])

def _ads_mutate(token, resource, operations):
    cid = _cfg("ADS_CUSTOMER_ID")
    r = requests.post(
        f"https://googleads.googleapis.com/{ADS_VER}/customers/{cid}/{resource}:mutate",
        headers={
            "Authorization":   f"Bearer {token}",
            "developer-token": _cfg("ADS_DEV_TOKEN"),
            "Content-Type":    "application/json"
        },
        json={"operations": operations}, timeout=20
    )
    if not r.ok:
        print(f"[AUDIT] Mutate {resource} error {r.status_code}: {r.text[:600]}")
        return False
    return True

def _wp_auth():
    user = _cfg_soft("WP_USER")
    pw   = _cfg_soft("WP_APP_PASS")
    if not user or not pw:
        return None
    return base64.b64encode(f"{user}:{pw}".encode()).decode()


# ── GSC ──────────────────────────────────────────────────────────────

def _gsc_query(token, body):
    site_enc = url_quote(GSC_SITE, safe="")
    url = (f"https://searchconsole.googleapis.com/webmasters/v3/sites/"
           f"{site_enc}/searchAnalytics/query")
    r = requests.post(url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body, timeout=20)
    return r.json().get("rows", []) if r.ok else []

def _audit_gsc(token):
    hoy   = date.today()
    fin   = (hoy - timedelta(days=1)).isoformat()
    ini7  = (hoy - timedelta(days=8)).isoformat()
    ini14 = (hoy - timedelta(days=15)).isoformat()
    ini30 = (hoy - timedelta(days=31)).isoformat()

    # Money queries últimos 7 días
    queries_7d = _gsc_query(token, {
        "startDate": ini7, "endDate": fin, "dimensions": ["query"],
        "dimensionFilterGroups": [{"filters": [{"dimension": "query",
            "operator": "includingRegex",
            "expression": "trasplante|injerto|capilar|pelo|turqu|estambul|fue|dhi"}]}],
        "rowLimit": 50
    })

    # Money queries semana anterior (comparativa caídas)
    queries_prev = _gsc_query(token, {
        "startDate": ini14, "endDate": ini7, "dimensions": ["query"],
        "dimensionFilterGroups": [{"filters": [{"dimension": "query",
            "operator": "includingRegex",
            "expression": "trasplante|injerto|capilar|pelo|turqu|estambul|fue|dhi"}]}],
        "rowLimit": 50
    })
    prev_map = {r["keys"][0]: r.get("position", 99) for r in queries_prev}

    # Páginas últimos 30 días — todas
    pages_30d = _gsc_query(token, {
        "startDate": ini30, "endDate": fin,
        "dimensions": ["page"], "rowLimit": 500
    })
    pages_map = {p["keys"][0]: p for p in pages_30d}

    # Páginas débiles: pos >15, CTR <1.5%, impresiones >30 → candidatas a reescribir meta
    weak_meta = [p for p in pages_30d
                 if p.get("position", 0) > 15
                 and p.get("ctr", 1) < 0.015
                 and p.get("impressions", 0) > 30
                 and "/blog/" in p["keys"][0]]  # solo blog, no tocar landings sin análisis

    # Páginas sin impresiones en 30 días → IndexNow re-crawl
    # (comparamos con un set de URLs conocidas del sitemap)
    zero_impression_pages = []
    try:
        sm = requests.get(f"{SITE}/sitemap_index.xml", timeout=8)
        import re as _re
        sitemaps = _re.findall(r'<loc>(.*?)</loc>', sm.text)
        for sm_url in sitemaps[:5]:
            sr = requests.get(sm_url, timeout=8)
            urls_in_sm = _re.findall(r'<loc>(.*?)</loc>', sr.text)
            for u in urls_in_sm:
                if u not in pages_map and "/blog/" in u:
                    zero_impression_pages.append(u)
        zero_impression_pages = list(set(zero_impression_pages))[:80]
    except Exception as e:
        print(f"[AUDIT] Sitemap error: {e}")

    # Detección caídas de posición en money queries (>3 puestos)
    position_drops = []
    for row in queries_7d:
        q   = row["keys"][0]
        pos = row.get("position", 99)
        prev = prev_map.get(q)
        if prev and (pos - prev) > 3:
            position_drops.append((q, round(prev, 1), round(pos, 1)))

    # Páginas con CTR bajo en posición media (alertas, no tocar)
    alert_pages = sorted(
        [p for p in pages_30d if 5 < p.get("position", 0) <= 15
         and p.get("ctr", 1) < 0.02 and p.get("impressions", 0) > 100],
        key=lambda p: p.get("impressions", 0), reverse=True
    )[:5]

    return queries_7d, weak_meta[:5], zero_impression_pages, position_drops, alert_pages


# ── Google Ads ───────────────────────────────────────────────────────

def _audit_ads(token):
    # Campañas activas
    camps = _gaql(token, "SELECT campaign.id FROM campaign WHERE campaign.status = 'ENABLED'")
    cids  = [row["campaign"]["id"] for row in camps]

    # Search terms últimos 7 días
    terms = _gaql(token,
        "SELECT search_term_view.search_term, search_term_view.status, metrics.clicks "
        "FROM search_term_view WHERE segments.date DURING LAST_7_DAYS "
        "AND metrics.clicks > 0 ORDER BY metrics.clicks DESC LIMIT 300")

    # Rendimiento campaña
    perf = _gaql(token,
        "SELECT campaign.name, metrics.clicks, metrics.impressions, metrics.ctr, "
        "metrics.conversions, metrics.cost_micros, metrics.search_impression_share "
        "FROM campaign WHERE segments.date DURING LAST_7_DAYS AND campaign.status = 'ENABLED'")

    # RSA con fuerza y estado de aprobación
    rsa_rows = _gaql(token,
        "SELECT ad_group_ad.resource_name, ad_group_ad.ad_strength, "
        "ad_group_ad.policy_summary.approval_status, "
        "ad_group_ad.ad.responsive_search_ad.headlines, "
        "ad_group_ad.ad.responsive_search_ad.descriptions, "
        "ad_group_ad.ad.resource_name "
        "FROM ad_group_ad WHERE ad_group_ad.status = 'ENABLED' "
        "AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'")

    # Análisis por hora (últimos 30 días) para dayparting
    hourly = _gaql(token,
        "SELECT segments.hour, metrics.clicks, metrics.conversions, metrics.cost_micros "
        "FROM campaign WHERE segments.date DURING LAST_30_DAYS "
        "AND campaign.status = 'ENABLED'")

    # Keywords caras con muy bajo CTR: gasto >8€ Y clics <3 en 30 días
    # (señal de mala calidad/relevancia — NO se usa conversión porque a nivel kw
    #  la atribución data-driven distribuye el crédito y casi todas muestran 0,
    #  aunque la campaña global tenga conversiones reales)
    waste_kw = _gaql(token,
        "SELECT ad_group_criterion.keyword.text, metrics.cost_micros, "
        "metrics.clicks, metrics.impressions, metrics.average_cpc "
        "FROM keyword_view WHERE segments.date DURING LAST_30_DAYS "
        "AND metrics.cost_micros > 8000000 AND metrics.clicks < 3 "
        "AND ad_group_criterion.status = 'ENABLED'")

    # CPA campaña global últimos 30 días (referencia real)
    camp_perf_30d = _gaql(token,
        "SELECT metrics.conversions, metrics.cost_micros, metrics.clicks "
        "FROM campaign WHERE segments.date DURING LAST_30_DAYS "
        "AND campaign.status = 'ENABLED'")

    return cids, terms, perf, rsa_rows, hourly, waste_kw, camp_perf_30d


# ── 🟢 Ejecutar: Negativos ───────────────────────────────────────────

def _detect_negatives(terms_rows):
    neg = set()
    for row in terms_rows:
        t      = row.get("searchTermView", {}).get("searchTerm", "").lower().strip()
        status = row.get("searchTermView", {}).get("status", "")
        if not t or status == "ADDED":
            continue
        tiene_geo = any(g in t for g in _GEO_TERMS)
        es_comp   = any(c in t for c in _COMPETITOR_TERMS)
        es_irrel  = any(i in t for i in _IRRELEVANT)
        if not tiene_geo or es_comp or es_irrel:
            neg.add(t)
    return list(neg)

def _add_negatives(token, cids, negativos):
    if not negativos or not cids:
        return []
    cid      = _cfg("ADS_CUSTOMER_ID")
    camp_res = f"customers/{cid}/campaigns/{cids[0]}"
    ops = [{"create": {"campaign": camp_res, "negative": True,
                       "keyword": {"text": t, "matchType": "EXACT"}}}
           for t in negativos[:30]]
    ok = _ads_mutate(token, "campaignCriteria", ops)
    if ok:
        added = [op["create"]["keyword"]["text"] for op in ops]
        print(f"[AUDIT] Negativos añadidos: {added}")
        return added
    return []


# ── 🟢 Ejecutar: Pausar anuncios DISAPPROVED ─────────────────────────

def _pause_disapproved(token, rsa_rows):
    to_pause = [
        row["adGroupAd"]["resourceName"] for row in rsa_rows
        if row.get("adGroupAd", {}).get("policySummary", {}).get("approvalStatus") == "DISAPPROVED"
    ]
    if not to_pause:
        return []
    ops = [{"update": {"resourceName": rn, "status": "PAUSED"},
            "updateMask": "status"} for rn in to_pause]
    ok = _ads_mutate(token, "adGroupAds", ops)
    paused = to_pause if ok else []
    if paused:
        print(f"[AUDIT] Anuncios DISAPPROVED pausados: {len(paused)}")
    return paused


# ── 🟢 Ejecutar: Mejorar RSA con nuevos headlines ────────────────────

def _improve_rsa(token, rsa_rows):
    improved = []
    for row in rsa_rows:
        ad_data = row.get("adGroupAd", {})
        strength = ad_data.get("adStrength", "")
        if strength not in ("POOR", "AVERAGE"):
            continue

        rsa   = ad_data.get("ad", {}).get("responsiveSearchAd", {})
        ad_rn = ad_data.get("ad", {}).get("resourceName", "")
        if not ad_rn:
            continue

        existing_hl_objs   = rsa.get("headlines", [])
        existing_headlines = [h.get("text", "") for h in existing_hl_objs]
        existing_descs     = rsa.get("descriptions", [])

        # Sólo actuar si tiene menos de 13 headlines (margen para añadir 2)
        if len(existing_hl_objs) >= 13:
            continue

        # Encontrar headlines del banco que no estén ya
        to_add = [{"text": h} for h in RSA_HEADLINES
                  if h not in existing_headlines][:2]
        if not to_add:
            continue

        # Preservar objetos completos (con pinnedField) para no romper pins existentes
        updated_headlines = list(existing_hl_objs) + to_add

        # Añadir descriptions si tiene menos de 3
        updated_descs = list(existing_descs)
        if len(existing_descs) < 3:
            existing_desc_texts = [d.get("text", "") for d in existing_descs]
            for d in RSA_DESCRIPTIONS:
                if d not in existing_desc_texts and len(updated_descs) < 4:
                    updated_descs.append({"text": d})

        cid = _cfg("ADS_CUSTOMER_ID")
        ops = [{
            "update": {
                "resourceName": ad_rn,
                "responsiveSearchAd": {
                    "headlines":    updated_headlines,
                    "descriptions": updated_descs
                }
            },
            "updateMask": "responsive_search_ad.headlines,responsive_search_ad.descriptions"
        }]
        ok = _ads_mutate(token, "ads", ops)
        if ok:
            improved.append(ad_rn)
            print(f"[AUDIT] RSA mejorado: {ad_rn} (+{len(to_add)} headlines)")

    return improved


# ── 🟢 Ejecutar: Reescribir metas débiles via WP API ─────────────────

def _slug_to_keyword(url):
    """Extrae keyword legible del slug de la URL."""
    slug = url.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").title()

def _generate_meta(url):
    kw = _slug_to_keyword(url)
    title = f"{kw} | Dr. Çelik — GHH Estambul"[:60]
    desc  = (f"{kw} con médico licenciado en Estambul. "
             f"+22 años de experiencia. FUE Zafiro y DHI. Consulta gratuita.")[:155]
    return title, desc

def _rewrite_weak_metas(weak_pages):
    auth = _wp_auth()
    if not auth:
        print("[AUDIT] WP_USER/WP_APP_PASS no configurados — saltando metas")
        return []
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type":  "application/json"
    }
    rewritten = []
    for page in weak_pages[:5]:
        url  = page["keys"][0]
        slug = url.rstrip("/").split("/")[-1]
        # Buscar post por slug
        try:
            r = requests.get(
                f"{SITE}/wp-json/wp/v2/posts",
                params={"slug": slug, "_fields": "id,slug"},
                headers=headers, timeout=10
            )
            posts = r.json() if r.ok else []
            if not posts:
                # Intentar como página
                r2 = requests.get(
                    f"{SITE}/wp-json/wp/v2/pages",
                    params={"slug": slug, "_fields": "id,slug"},
                    headers=headers, timeout=10
                )
                posts = r2.json() if r2.ok else []
            if not posts:
                continue
            post_id = posts[0]["id"]
            title, desc = _generate_meta(url)
            pr = requests.post(
                f"{SITE}/wp-json/wp/v2/posts/{post_id}",
                headers=headers,
                json={"meta": {
                    "_yoast_wpseo_title":    title,
                    "_yoast_wpseo_metadesc": desc
                }},
                timeout=10
            )
            if pr.ok:
                rewritten.append({"url": url, "title": title})
                print(f"[AUDIT] Meta reescrita: {slug}")
        except Exception as e:
            print(f"[AUDIT] Error meta {slug}: {e}")
    return rewritten


# ── 🟢 Ejecutar: IndexNow ─────────────────────────────────────────────

def _submit_indexnow(urls):
    key = _cfg_soft("INDEXNOW_KEY")
    if not key or not urls:
        return 0
    batch = urls[:50]
    try:
        r = requests.post("https://api.indexnow.org/indexnow", json={
            "host":    "trasplantepeloturquia.com",
            "key":     key,
            "keyLocation": f"{SITE}/{key}.txt",
            "urlList": batch
        }, timeout=15)
        if r.ok or r.status_code == 202:
            print(f"[AUDIT] IndexNow: {len(batch)} URLs enviadas")
            return len(batch)
    except Exception as e:
        print(f"[AUDIT] IndexNow error: {e}")
    return 0


# ── Análisis dayparting ───────────────────────────────────────────────

def _analyze_hourly(hourly_rows):
    """Detecta horas con gasto >2€ y 0 conversiones en 30 días."""
    by_hour = {}
    for row in hourly_rows:
        h    = row.get("segments", {}).get("hour", 0)
        m    = row.get("metrics", {})
        cost = int(m.get("costMicros", 0)) / 1_000_000
        conv = float(m.get("conversions", 0))
        if h not in by_hour:
            by_hour[h] = {"cost": 0, "conv": 0, "clicks": 0}
        by_hour[h]["cost"]   += cost
        by_hour[h]["conv"]   += conv
        by_hour[h]["clicks"] += int(m.get("clicks", 0))
    waste_hours = [(h, d["cost"], d["clicks"])
                   for h, d in by_hour.items()
                   if d["cost"] > 2 and d["conv"] < 0.1]
    waste_hours.sort(key=lambda x: -x[1])
    return waste_hours


# ── Main ──────────────────────────────────────────────────────────────

def run_daily_audit():
    """Punto de entrada APScheduler. 07:00 Atlantic/Canary."""
    hoy = date.today()
    hoy_str = hoy.strftime("%d/%m/%Y")
    print(f"[AUDIT] === Auditoría diaria GHH {hoy_str} ===")

    ejecutado   = []
    recomendado = []

    try:
        token = _get_token()
    except Exception as e:
        _send_telegram(f"GHH AUDIT {hoy_str} — ❌ Error token OAuth: {e}")
        return

    # ── GSC ─────────────────────────────────────────────────────────
    queries_7d = []; weak_meta = []; zero_pages = []; drops = []; alert_pages = []
    try:
        queries_7d, weak_meta, zero_pages, drops, alert_pages = _audit_gsc(token)
    except Exception as e:
        print(f"[AUDIT] GSC error: {e}")

    # ── Ads data ─────────────────────────────────────────────────────
    cids=[]; terms=[]; perf=[]; rsa_rows=[]; hourly=[]; waste_kw=[]; camp_perf_30d=[]
    try:
        cids, terms, perf, rsa_rows, hourly, waste_kw, camp_perf_30d = _audit_ads(token)
    except Exception as e:
        print(f"[AUDIT] Ads error: {e}")

    # CPA global 30 días — referencia para no flagear keywords por "0 conv" individual
    _total_conv_30d = sum(float(r.get("metrics", {}).get("conversions", 0)) for r in camp_perf_30d)
    _total_cost_30d = sum(int(r.get("metrics", {}).get("costMicros", 0)) for r in camp_perf_30d) / 1_000_000
    _camp_cpa_30d   = round(_total_cost_30d / _total_conv_30d, 2) if _total_conv_30d > 0 else None
    _camp_ok        = _total_conv_30d >= 5 and (_camp_cpa_30d or 999) < 25  # campaña sana

    # ── 🟢 EJECUTAR ─────────────────────────────────────────────────

    # 1. Negativos Ads sin geo
    try:
        neg = _detect_negatives(terms)
        if neg:
            added = _add_negatives(token, cids, neg)
            if added:
                ejecutado.append(f"➕ {len(added)} negativos Ads añadidos:\n"
                                 + "\n".join(f"  - {n}" for n in added[:10]))
    except Exception as e:
        print(f"[AUDIT] Error negativos: {e}")

    # 2. Pausar anuncios DISAPPROVED
    try:
        paused = _pause_disapproved(token, rsa_rows)
        if paused:
            ejecutado.append(f"⏸ {len(paused)} anuncio(s) DISAPPROVED pausado(s)")
    except Exception as e:
        print(f"[AUDIT] Error pause disapproved: {e}")

    # 3. Mejorar RSA (headlines + descriptions)
    try:
        improved = _improve_rsa(token, rsa_rows)
        if improved:
            ejecutado.append(f"📝 RSA mejorado(s): {len(improved)} (headlines + descriptions añadidos)")
    except Exception as e:
        print(f"[AUDIT] Error RSA improve: {e}")

    # 4. Reescribir metas SEO débiles (solo blog, pos >15)
    try:
        rewritten = _rewrite_weak_metas(weak_meta)
        if rewritten:
            lines = "\n".join(f"  - {r['url'].split('/')[-2]}: {r['title']}" for r in rewritten)
            ejecutado.append(f"🔤 {len(rewritten)} metas reescritas (CTR <1.5%, pos >15):\n{lines}")
    except Exception as e:
        print(f"[AUDIT] Error metas: {e}")

    # 5. IndexNow — páginas sin impresiones en 30 días
    try:
        if zero_pages:
            sent = _submit_indexnow(zero_pages)
            if sent:
                ejecutado.append(f"📡 IndexNow: {sent} URLs sin impresiones enviadas a rerastreo")
    except Exception as e:
        print(f"[AUDIT] Error IndexNow: {e}")

    # ── 🔴 REPORTAR ─────────────────────────────────────────────────

    # Caídas de posición en money queries
    for q, prev_p, curr_p in drops[:5]:
        recomendado.append(f"📉 Caída: '{q}' pos {prev_p} → {curr_p} (−{round(curr_p-prev_p,1)})")

    # Keywords cara + bajo engagement (gasto >8€ y <3 clics = mala relevancia/QS)
    # NOTA: NO se usa "0 conversiones" como criterio — la atribución data-driven
    # distribuye el crédito a nivel campaña, no keyword. La campaña sí convierte.
    for row in waste_kw[:5]:
        kw     = row.get("adGroupCriterion", {}).get("keyword", {}).get("text", "?")
        cost   = int(row.get("metrics", {}).get("costMicros", 0)) / 1_000_000
        clics  = int(row.get("metrics", {}).get("clicks", 0))
        avg_cpc= int(row.get("metrics", {}).get("averageCpc", 0)) / 1_000_000
        recomendado.append(
            f"🔍 KW cara/baja-relevancia: '{kw}' — {round(cost,1)}€ / {clics} clics "
            f"(CPC {round(avg_cpc,2)}€) → revisar QS o añadir como negativa"
        )

    # Dayparting: horas con gasto pero sin conversiones atribuidas
    # Solo reportar si la campaña está sana (hay conv globales) Y el gasto/hora es alto
    # No se recomienda pausar por esto — la atribución puede no mostrar conv por hora
    waste_hours = _analyze_hourly(hourly)
    if _camp_ok:  # solo reportar si hay conversiones globales reales
        for h, cost, clicks in waste_hours[:3]:
            recomendado.append(
                f"⏰ Hora {h}h: {round(cost,1)}€ / {clicks} clics sin conv atribuida "
                f"→ revisar si justifica ajuste de puja (no pausar)"
            )

    # Páginas alert (pos 5-15, CTR bajo)
    for p in alert_pages[:3]:
        u = p["keys"][0].replace(SITE, "")
        recomendado.append(
            f"📊 Meta débil: {u} | pos {round(p.get('position',0),1)} "
            f"CTR {round(p.get('ctr',0)*100,1)}% | ¿mejorar title/H1?"
        )

    # RSA POOR sin mejorar (si improve_rsa no pudo actuar)
    for row in rsa_rows:
        st = row.get("adGroupAd", {}).get("adStrength", "")
        if st == "POOR":
            recomendado.append("⚠️ RSA con Ad Strength POOR aún pendiente — revisar Ads")
            break

    # ── Rendimiento SEM ──────────────────────────────────────────────
    sem_line = ""
    if perf:
        m    = perf[0].get("metrics", {})
        cli  = m.get("clicks", 0)
        conv = float(m.get("conversions", 0))
        cost = int(m.get("costMicros", 0)) / 1_000_000
        cpa  = round(cost / conv, 2) if conv > 0 else "—"
        ish  = round(float(m.get("searchImpressionShare", 0)) * 100, 1)
        sem_line = f"\n📈 *SEM 7d:* {cli} clics | {conv:.0f} conv | CPA {cpa}€ | IS {ish}%"

    # Estado global campaña 30 días (WhatsApp conversions reales)
    camp_status = ""
    if _total_conv_30d > 0:
        icon = "✅" if _camp_ok else "⚠️"
        camp_status = (f"\n{icon} *Campaña 30d:* {_total_conv_30d:.0f} conv WhatsApp | "
                       f"CPA {_camp_cpa_30d}€ | {round(_total_cost_30d,1)}€ invertidos")
        camp_status += ("\n⚠️ _Conversiones kw-individuales = 0 es NORMAL (Data-Driven Attribution "
                        "— el crédito se distribuye entre todos los touchpoints del embudo)_")

    # ── Money queries ─────────────────────────────────────────────────
    mq_lines = ""
    if queries_7d:
        idx = {r["keys"][0]: r for r in queries_7d}
        lines = []
        for mq in _MONEY_QUERIES:
            if mq in idx:
                q = idx[mq]
                lines.append(f"  {mq}: pos {round(q.get('position',0),1)} "
                              f"CTR {round(q.get('ctr',0)*100,1)}% {q.get('clicks',0)} clics")
        if lines:
            mq_lines = "\n🔍 *Money queries:*\n" + "\n".join(lines)

    # ── Si nada que reportar → salir silencioso ───────────────────────
    if not ejecutado and not recomendado:
        print("[AUDIT] Sin novedades. Telegram omitido.")
        return

    # ── Construir mensaje ─────────────────────────────────────────────
    msg = f"*GHH AUDIT — {hoy_str}*"
    msg += camp_status
    msg += sem_line
    msg += mq_lines

    if ejecutado:
        msg += "\n\n✅ *EJECUTADO AUTOMÁTICAMENTE:*\n"
        msg += "\n".join(ejecutado)

    if recomendado:
        msg += "\n\n⚠️ *REQUIERE TU OK:*\n"
        msg += "\n".join(recomendado)

    _send_telegram(msg)
    print(f"[AUDIT] Telegram enviado. Ejecutado: {len(ejecutado)} | Alertas: {len(recomendado)}")
