#!/usr/bin/env python3
"""
Script di Spegnimento Pubblico e Attivazione Privata Istantanea.
- Svuota silenziosamente tutti i feed pubblici in dist/ (zero VEVENT, zero avvisi di dismissione).
- Sostituisce dist/index.html con una schermata neutra vuota.
- Aggiunge robots.txt per disabilitare il crawl dei motori di ricerca.
- Estrae da EasyCourse UniSR unicamente il 3° Anno - Linea Viola (CdL 458, Anno 1084, Linea 1736).
- Genera i feed privati in dist/p_viola3/:
  1. apple_linea_viola.ics (Feed singolo cumulativo per Apple Calendar)
  2. materie/materia_<slug>.ics (Feed separati per materia per Google Calendar, con palette colori deterministica)
  3. elettivi/elettivo_<slug>.ics (Feed per corsi elettivi opzionali)
  4. index.html (Dashboard riservata con pulsanti 1-click per Apple e Google Calendar)
- Aggiorna config/active_mode.json a "mode": "private" per mantenere sincronizzati i feed privati nei successivi run di GitHub Actions.
"""

import os
import sys
import re
import ssl
import json
import time
import hashlib
import unicodedata
import urllib.request
from datetime import datetime, timezone
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, "dist")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "active_mode.json")

PRIVATE_TOKEN = "p_viola3"
PRIVATE_DIR = os.path.join(DIST_DIR, PRIVATE_TOKEN)

PALETTE = [
    ('#facc15', '#fef08a22', 'Banana'),
    ('#c084fc', '#c084fc22', 'Amethyst'),
    ('#f472b6', '#f472b622', 'Cherry Blossom'),
    ('#4ade80', '#4ade8022', 'Eucalyptus'),
    ('#60a5fa', '#60a5fa22', 'Peacock'),
    ('#f87171', '#f8717122', 'Tomato'),
    ('#2dd4bf', '#2dd4bf22', 'Sage'),
    ('#818cf8', '#818cf822', 'Blueberry'),
    ('#a78bfa', '#a78bfa22', 'Grape'),
    ('#34d399', '#34d39922', 'Basil'),
    ('#fbbf24', '#fbbf2422', 'Mango'),
    ('#94a3b8', '#94a3b822', 'Graphite'),
]


def get_color_for_subject(subject_name):
    h = int(hashlib.md5(subject_name.encode('utf-8')).hexdigest(), 16)
    return PALETTE[h % len(PALETTE)]


def purge_public_calendars():
    """Sovrascrive tutti i feed pubblici con calendari RFC 5545 formalmente validi privi di eventi."""
    print("[1/5] Svuotamento silenzioso di tutti i feed pubblici...")
    count_purged = 0
    
    if not os.path.exists(DIST_DIR):
        os.makedirs(DIST_DIR, exist_ok=True)
        return 0

    for root, dirs, files in os.walk(DIST_DIR):
        # Non toccare la cartella privata
        if PRIVATE_TOKEN in root:
            continue
        for f in files:
            if f.endswith(".ics"):
                file_path = os.path.join(root, f)
                # Estrai calname originale se possibile
                cal_name = "Calendario UniSR"
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as ics_in:
                        for line in ics_in:
                            if line.startswith("X-WR-CALNAME:"):
                                cal_name = line.replace("X-WR-CALNAME:", "").strip()
                                break
                except Exception:
                    pass

                empty_ics = (
                    "BEGIN:VCALENDAR\r\n"
                    "VERSION:2.0\r\n"
                    "PRODID:-//UniSR//Calendari Medicina//IT\r\n"
                    "CALSCALE:GREGORIAN\r\n"
                    "METHOD:PUBLISH\r\n"
                    f"X-WR-CALNAME:{cal_name}\r\n"
                    "X-WR-TIMEZONE:Europe/Rome\r\n"
                    "END:VCALENDAR\r\n"
                )
                with open(file_path, "w", encoding="utf-8") as ics_out:
                    ics_out.write(empty_ics)
                count_purged += 1

    # Neutralizzazione index.html e ui_data.json pubblici
    index_path = os.path.join(DIST_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f_index:
        f_index.write("<!DOCTYPE html><html><head><meta charset='UTF-8'><title></title></head><body></body></html>")

    ui_data_path = os.path.join(DIST_DIR, "ui_data.json")
    if os.path.exists(ui_data_path):
        with open(ui_data_path, "w", encoding="utf-8") as f_ui:
            f_ui.write("[]")

    # robots.txt per disabilitare indicizzazione
    robots_path = os.path.join(DIST_DIR, "robots.txt")
    with open(robots_path, "w", encoding="utf-8") as f_robots:
        f_robots.write("User-agent: *\nDisallow: /\n")

    print(f" -> {count_purged} file .ics pubblici svuotati con successo.")
    print(" -> dist/index.html neutralizzato.")
    print(" -> dist/robots.txt creato.")
    return count_purged


def fetch_viola_lessons():
    """Estrae le lezioni del 3° Anno Linea Viola da EasyCourse UniSR."""
    print("[2/5] Interrogazione EasyCourse UniSR (Medicina 3 - Linea Viola)...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    cdl_id = 458
    anno_id = 1084
    curr_id = 1736

    url = (
        f"https://easycourse.unisr.it/easycourse-new/pubblicazioni-riservate/standardGrid/"
        f"figlia-4/2026-2027/s1/riservato?"
        f"catena=S1&ricercaIndex=Corso+di+studi&CorsoDiStudio={cdl_id}&annoCorso={anno_id}&curriculum={curr_id}&settimana=all"
    )
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    )
    html = ""
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=40) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                break
        except Exception as e:
            if attempt == 2:
                print(f"[ERRORE] Impossibile contattare EasyCourse: {e}")
                return []
            time.sleep(2)

    # Parsing blocchi giornalieri
    giorno_blocks = re.findall(
        r'<div[^>]*class="giorno-container\s*([^"]*)"[^>]*>(.*?)(?=<div[^>]*class="giorno-container|<div[^>]*class="easy-ph|<!-- ================= DESKTOP|$)',
        html,
        re.DOTALL
    )
    all_lessons = []
    seen = set()

    for classes, g_content in giorno_blocks:
        if "senza-lezioni" in classes:
            continue
        d_match = re.search(r'(\d{2}-\d{2}-\d{4})', g_content[:1000])
        if not d_match:
            continue
        giorno_data = d_match.group(1)

        lez_wrap = re.search(r'<div[^>]*class="lezioni-giornaliere"[^>]*>(.*)', g_content, re.DOTALL)
        if not lez_wrap:
            continue

        lezioni_tags = re.findall(r'<div[^>]*class="lezione"[^>]*>', lez_wrap.group(1))
        for l in lezioni_tags:
            def get_attr(name):
                m = re.search(rf'data-{name}="([^"]*)"', l)
                return m.group(1).strip() if m else ""

            ora_ini = get_attr("ora-inizio")
            ora_fine = get_attr("ora-fine")
            titolo = get_attr("titolo")
            aula = get_attr("aula")
            sede = get_attr("sede")
            docenti_json = get_attr("docenti")
            lesson_id = get_attr("id")

            nomi_docenti = []
            if docenti_json:
                try:
                    doc_data = json.loads(docenti_json)
                    for d in doc_data:
                        nome = f"{d.get('Nome', '')} {d.get('Cognome', '')}".strip()
                        if nome:
                            nomi_docenti.append(nome)
                except Exception:
                    pass

            is_elettivo = 'elettiv' in titolo.lower()

            key = (giorno_data, ora_ini, ora_fine, titolo, sede, aula)
            if key in seen:
                continue
            seen.add(key)

            all_lessons.append({
                'id': lesson_id,
                'date': giorno_data,
                'ora_inizio': ora_ini,
                'ora_fine': ora_fine,
                'titolo': titolo,
                'aula': aula,
                'sede': sede,
                'docenti': nomi_docenti,
                'elettivo': is_elettivo
            })

    def sort_key(x):
        d, m, y = x['date'].split('-')
        return f"{y}{m}{d}_{x['ora_inizio']}"

    all_lessons.sort(key=sort_key)
    print(f" -> Estratte {len(all_lessons)} lezioni totali per Medicina 3 - Linea Viola.")
    return all_lessons


def clean_title(raw_title):
    tipo = ""
    if " - LEZ" in raw_title or " - LEZ_D" in raw_title:
        tipo = "Lezione"
    elif " - ESE" in raw_title:
        tipo = "Esercitazione"
    elif " - APR" in raw_title or " - TIR" in raw_title:
        tipo = "Attività Pratica"
    
    base_match = re.match(r'^(.*?)(?:\s*\[|\s*-)', raw_title)
    base_name = base_match.group(1).strip() if base_match else raw_title
    if tipo:
        return f"{base_name} [{tipo}]"
    return base_name


def get_base_subject_name(cleaned_title):
    m = re.match(r'^(.*?)\s*\[', cleaned_title)
    if m:
        return m.group(1).strip()
    return cleaned_title


def slugify(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '_', text)


def generate_uid(lesson):
    unique_key = f"{lesson['date']}_{lesson['ora_inizio']}_{lesson['ora_fine']}_{lesson['titolo']}_{lesson['sede']}_{lesson['aula']}"
    h = hashlib.sha256(unique_key.encode('utf-8')).hexdigest()[:16]
    return f"unisr-med-{h}@easycourse.unisr.it"


def format_ical_dt(date_str, time_str):
    day, month, year = date_str.split('-')
    hour, minute = time_str.split(':')
    return f"{year}{month}{day}T{hour}{minute}00"


def escape_ical_text(text):
    if not text:
        return ""
    text = text.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')
    return text


def build_ics_calendar(calendar_name, lessons, description=""):
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//UniSR//Calendari Medicina//IT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ical_text(calendar_name)}",
        f"X-WR-CALDESC:{escape_ical_text(description)}",
        "X-WR-TIMEZONE:Europe/Rome",
        "BEGIN:VTIMEZONE",
        "TZID:Europe/Rome",
        "X-LIC-LOCATION:Europe/Rome",
        "BEGIN:DAYLIGHT",
        "TZOFFSETFROM:+0100",
        "TZOFFSETTO:+0200",
        "TZNAME:CEST",
        "DTSTART:19700329T020000",
        "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
        "END:DAYLIGHT",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:+0200",
        "TZOFFSETTO:+0100",
        "TZNAME:CET",
        "DTSTART:19701025T030000",
        "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]
    for l in lessons:
        dtstart = format_ical_dt(l['date'], l['ora_inizio'])
        dtend = format_ical_dt(l['date'], l['ora_fine'])
        uid = generate_uid(l)
        summary = clean_title(l['titolo'])

        loc_parts = []
        if l['sede']: loc_parts.append(f"Edificio {l['sede']}")
        if l['aula']: loc_parts.append(f"Aula {l['aula']}")
        location = ", ".join(loc_parts)

        desc_lines = [f"Insegnamento: {l['titolo']}"]
        if l['docenti']: desc_lines.append(f"Docenti: {', '.join(l['docenti'])}")
        if location: desc_lines.append(f"Luogo: {location}")
        desc_lines.append(f"Orario: {l['ora_inizio']} - {l['ora_fine']}")
        desc_lines.append("Fonte: EasyCourse UniSR (Privato)")

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            f"DTSTART;TZID=Europe/Rome:{dtstart}",
            f"DTEND;TZID=Europe/Rome:{dtend}",
            f"SUMMARY:{escape_ical_text(summary)}",
            f"LOCATION:{escape_ical_text(location)}",
            f"DESCRIPTION:{escape_ical_text(chr(10).join(desc_lines))}",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT"
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def generate_private_feeds(lessons):
    """Costruisce la directory privata con Apple Calendar singolo + Google Calendar per materia."""
    print("[3/5] Generazione feed privati (Apple Calendar singolo + Google per materia)...")
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    materie_dir = os.path.join(PRIVATE_DIR, "materie")
    elettivi_dir = os.path.join(PRIVATE_DIR, "elettivi")
    os.makedirs(materie_dir, exist_ok=True)
    os.makedirs(elettivi_dir, exist_ok=True)

    curricular = [l for l in lessons if not l['elettivo']]
    electives = [l for l in lessons if l['elettivo']]

    # 1. Feed Unico per Apple Calendar (Tutti i curricolari)
    apple_file = "apple_linea_viola.ics"
    apple_path = os.path.join(PRIVATE_DIR, apple_file)
    with open(apple_path, "w", encoding="utf-8") as f:
        f.write(build_ics_calendar("UniSR Med3 - Linea Viola", curricular, "Calendario Completo Curricolare"))
    print(f" -> Creato feed Apple: {apple_file} ({len(curricular)} lezioni)")

    # 2. Feed separati per materia (Google Calendar)
    subjects = defaultdict(list)
    for l in curricular:
        s = get_base_subject_name(clean_title(l['titolo']))
        subjects[s].append(l)

    materie_ui = []
    for s_name, s_lessons in sorted(subjects.items()):
        slug = slugify(s_name)
        f_name = f"materia_{slug}.ics"
        f_path = os.path.join(materie_dir, f_name)
        color_hex, bg_hex, color_name = get_color_for_subject(s_name)
        with open(f_path, "w", encoding="utf-8") as f:
            f.write(build_ics_calendar(f"{s_name}", s_lessons, f"Insegnamento: {s_name}"))
        materie_ui.append({
            "name": s_name,
            "filename": f"materie/{f_name}",
            "count": len(s_lessons),
            "color_name": color_name,
            "color_hex": color_hex,
            "bg_hex": bg_hex
        })
        print(f" -> Materia Google: {s_name} ({len(s_lessons)} lez) -> {color_name}")

    # 3. Feed separati per elettivi
    elettivi_subjects = defaultdict(list)
    for l in electives:
        s = get_base_subject_name(clean_title(l['titolo']))
        elettivi_subjects[s].append(l)

    elettivi_ui = []
    for e_name, e_lessons in sorted(elettivi_subjects.items()):
        slug = slugify(e_name)
        f_name = f"elettivo_{slug}.ics"
        f_path = os.path.join(elettivi_dir, f_name)
        with open(f_path, "w", encoding="utf-8") as f:
            f.write(build_ics_calendar(f"Elettivo: {e_name}", e_lessons, f"Corso Elettivo: {e_name}"))
        elettivi_ui.append({
            "name": e_name,
            "filename": f"elettivi/{f_name}",
            "count": len(e_lessons),
            "color_name": "Tangerine",
            "color_hex": "#fb923c",
            "bg_hex": "#fb923c22"
        })
        print(f" -> Elettivo: {e_name} ({len(e_lessons)} lez)")

    # 4. Generazione Dashboard Privata index.html
    print("[4/5] Creazione interfaccia web riservata (p_viola3/index.html)...")
    private_html = generate_private_html(apple_file, len(curricular), materie_ui, elettivi_ui)
    with open(os.path.join(PRIVATE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(private_html)
    print(" -> Dashboard privata salvata.")


def generate_private_html(apple_file, apple_count, materie, elettivi):
    materie_json = json.dumps(materie, ensure_ascii=False)
    elettivi_json = json.dumps(elettivi, ensure_ascii=False)
    
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calendari UniSR - Medicina 3 (Linea Viola)</title>
    <style>
        :root {{
            --bg: #0f172a; --surface: #1e293b; --surface-hover: #334155;
            --text: #f8fafc; --text-muted: #94a3b8; --primary: #38bdf8;
            --border: #334155; --orange: #fb923c;
            --apple: #0284c7; --google: #1a73e8; --outlook: #0078d4;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        body {{ background: var(--bg); color: var(--text); padding: 2rem 1rem; line-height: 1.5; }}
        .container {{ max-width: 980px; margin: 0 auto; }}
        header {{ text-align: center; margin-bottom: 2rem; }}
        h1 {{ font-size: 2.1rem; margin-bottom: 0.5rem; color: #fff; }}
        .subtitle {{ color: var(--text-muted); font-size: 1.15rem; }}
        
        .pill-banner {{
            background: #1e1b4b; border: 1px solid #6366f1; border-radius: 12px;
            padding: 0.9rem 1.25rem; margin-bottom: 2rem; display: flex;
            align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem;
        }}
        .pill-tag {{
            font-size: 0.8rem; font-weight: 700; color: #a5b4fc; background: #312e81;
            padding: 0.25rem 0.6rem; border-radius: 6px; text-transform: uppercase;
        }}

        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.25rem; margin-bottom: 2.5rem; }}
        .card {{
            background: var(--surface); border: 1px solid var(--border);
            border-radius: 14px; padding: 1.35rem; display: flex; flex-direction: column; justify-content: space-between;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}
        .card:hover {{ transform: translateY(-2px); border-color: #475569; }}
        .card-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; gap: 0.5rem; }}
        .card-header h3 {{ font-size: 1.1rem; font-weight: 600; flex-grow: 1; }}
        .badge {{ font-size: 0.75rem; font-weight: 700; padding: 0.25rem 0.6rem; border-radius: 6px; text-transform: uppercase; white-space: nowrap; }}
        .card-meta {{ font-size: 0.85rem; color: #cbd5e1; margin-bottom: 1rem; }}
        .actions {{ display: flex; flex-direction: column; gap: 0.5rem; }}
        .actions-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }}
        
        .btn {{
            display: flex; align-items: center; justify-content: center; gap: 0.4rem;
            text-align: center; padding: 0.6rem 0.8rem; border-radius: 8px;
            font-size: 0.82rem; font-weight: 600; text-decoration: none; cursor: pointer;
            border: none; transition: opacity 0.2s;
        }}
        .btn:hover {{ opacity: 0.9; }}
        .btn-apple {{ background: #0284c7; color: white; }}
        .btn-gcal {{ background: #2563eb; color: white; }}
        .btn-outlook {{ background: #0284c7; color: white; }}
        .btn-copy {{ background: var(--surface-hover); color: #e2e8f0; border: 1px solid var(--border); width: 100%; }}
        
        .section-title {{ font-size: 1.35rem; margin: 2.2rem 0 1rem; color: #fff; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem; }}
        
        .guide-box {{
            background: var(--surface); border: 1px solid var(--border);
            border-radius: 14px; padding: 1.75rem; margin-top: 3rem;
        }}
        .guide-box h2 {{ font-size: 1.3rem; margin-bottom: 1rem; color: #fff; }}
        .platforms-grid {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.25rem; margin-top: 1rem;
        }}
        .platform-card {{
            background: #0f172a; border: 1px solid var(--border); border-radius: 10px; padding: 1rem;
        }}
        .platform-card h4 {{ font-size: 0.98rem; margin-bottom: 0.4rem; color: var(--primary); display: flex; align-items: center; gap: 0.4rem; }}
        .platform-card p, .platform-card li {{ font-size: 0.85rem; color: var(--text-muted); line-height: 1.4; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Sincronizzazione Calendario UniSR</h1>
            <p class="subtitle">Accesso Diretto Personale • Medicina e Chirurgia 3</p>
        </header>

        <div class="pill-banner">
            <div>
                <strong style="color:#fff; font-size:1rem;">Configurazione Attiva:</strong>
                <span style="color:#cbd5e1; margin-left:0.5rem;">3° Anno — Linea Viola (Canale C)</span>
            </div>
            <span class="pill-tag">Feed Riservato</span>
        </div>

        <!-- Box Calendario Completo Curricolare (Apple / iOS / Mac) -->
        <div class="card" style="border-color: var(--primary); background: #0b1329; margin-bottom: 2rem;">
            <div class="card-header">
                <span class="badge" style="background: #38bdf822; color: #38bdf8; border: 1px solid #38bdf8;">FEED UNICO COMPLETO</span>
                <h3 id="full-card-title">Tutti i Corsi Curricolari Obbligatori (Linea Viola)</h3>
            </div>
            <p class="card-meta"><b>{apple_count}</b> eventi curricolari obbligatori nel semestre</p>
            <div class="actions">
                <div class="actions-row">
                    <a id="apple-full-btn" href="#" class="btn btn-apple">🍏 Apple Calendar (iOS/Mac)</a>
                    <a id="gcal-full-btn" href="#" target="_blank" class="btn btn-gcal">📅 Google Calendar</a>
                </div>
                <div class="actions-row">
                    <a id="outlook-full-btn" href="#" target="_blank" class="btn btn-outlook">📧 Outlook / 365</a>
                    <button id="copy-full-btn" onclick="copyUrl('{apple_file}', this)" class="btn btn-copy">📋 Copia Link Universale (ICS)</button>
                </div>
            </div>
        </div>

        <!-- Moduli Obbligatori per Materia (Google Calendar / Multi-Colore) -->
        <h2 class="section-title">📚 Corsi per Materia (Google Calendar / Outlook / Multi-Colore)</h2>
        <p style="color:var(--text-muted); font-size:0.9rem; margin-top:-0.5rem; margin-bottom:1.25rem;">
            Sottoscrivi le singole materie per visualizzarle con i rispettivi colori nel tuo calendario.
        </p>
        <div class="grid" id="materie-grid"></div>

        <!-- Corsi Elettivi -->
        <h2 class="section-title">🎯 Corsi Elettivi (A scelta dello studente - Arancione)</h2>
        <p style="color:var(--text-muted); font-size:0.9rem; margin-top:-0.5rem; margin-bottom:1.25rem;">
            Sottoscrivi unicamente i corsi opzionali che avete inserito nel rispettivo piano di studi.
        </p>
        <div class="grid" id="elettivi-grid"></div>

        <!-- Guida Multi-Piattaforma -->
        <div class="guide-box">
            <h2>📱 Istruzioni Rapide per Dispositivo</h2>
            <div class="platforms-grid">
                <div class="platform-card">
                    <h4>🍏 Apple (iPhone, iPad, Mac)</h4>
                    <p>Clicca sul pulsante azzurro <b>"Apple Calendar"</b>. Il sistema aprirà automaticamente l'app Calendario. Sincronizzandosi con iCloud, apparirà su tutti i tuoi dispositivi e Apple Watch.</p>
                </div>
                <div class="platform-card">
                    <h4>📅 Google Calendar (Android / PC)</h4>
                    <p>Clicca su <b>"Google Calendar"</b> per aggiungerlo direttamente con 1 clic. Assegna il colore suggerito sul badge per mantenere l'ordine visivo.</p>
                </div>
                <div class="platform-card">
                    <h4>📧 Microsoft Outlook (Windows / Mac / Web)</h4>
                    <p>Clicca su <b>"Outlook / 365"</b> per aprire la sottoscrizione web, oppure copia il link ICS e incollalo in Outlook in <i>"Aggiungi calendario" ➔ "Iscriviti dal Web"</i>.</p>
                </div>
                <div class="platform-card">
                    <h4>📲 Samsung Calendar / Android Nativo</h4>
                    <p>Copia il link universale ICS e incollalo nell'app Calendario sotto <i>"Gestisci calendari" ➔ "Aggiungi da URL"</i>.</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        const materie = {materie_json};
        const elettivi = {elettivi_json};
        const baseUrl = window.location.href.replace(/[/]index[.]html$/, '').replace(/[/]$/, '');

        // Setup Feed Unico
        const appleFullUrl = baseUrl + '/{apple_file}?v=1';
        const cleanWebcal = appleFullUrl.replace(/^https?:[/][/]/, 'webcal://');
        const gcalFullUrl = 'https://calendar.google.com/calendar/render?cid=' + encodeURIComponent(cleanWebcal);
        const outlookFullUrl = 'https://outlook.live.com/calendar/0/addfromweb?url=' + encodeURIComponent(appleFullUrl) + '&name=' + encodeURIComponent('UniSR Med3 Linea Viola');

        document.getElementById('apple-full-btn').href = cleanWebcal;
        document.getElementById('gcal-full-btn').href = gcalFullUrl;
        document.getElementById('outlook-full-btn').href = outlookFullUrl;

        function buildCard(item) {{
            const itemIcsUrl = baseUrl + '/' + item.filename + '?v=1';
            const itemWebcal = itemIcsUrl.replace(/^https?:[/][/]/, 'webcal://');
            const gcalItemUrl = 'https://calendar.google.com/calendar/render?cid=' + encodeURIComponent(itemWebcal);
            const outlookItemUrl = 'https://outlook.live.com/calendar/0/addfromweb?url=' + encodeURIComponent(itemIcsUrl) + '&name=' + encodeURIComponent(item.name);
            
            return `
            <div class="card">
                <div class="card-header">
                    <span class="badge" style="background: ${{item.bg_hex}}; color: ${{item.color_hex}}; border: 1px solid ${{item.color_hex}};">${{item.color_name}}</span>
                    <h3>${{item.name}}</h3>
                </div>
                <p class="card-meta"><b>${{item.count}}</b> sessioni in calendario</p>
                <div class="actions">
                    <div class="actions-row">
                        <a href="${{gcalItemUrl}}" target="_blank" class="btn btn-gcal">📅 Google</a>
                        <a href="${{itemWebcal}}" class="btn btn-apple">🍏 Apple</a>
                    </div>
                    <div class="actions-row">
                        <a href="${{outlookItemUrl}}" target="_blank" class="btn btn-outlook">📧 Outlook</a>
                        <button onclick="copyUrl('${{item.filename}}', this)" class="btn btn-copy">📋 Copia ICS</button>
                    </div>
                </div>
            </div>`;
        }}

        document.getElementById('materie-grid').innerHTML = materie.map(buildCard).join('');
        document.getElementById('elettivi-grid').innerHTML = elettivi.map(buildCard).join('');

        window.copyUrl = function(file, btn) {{
            const url = baseUrl + '/' + file + '?v=1';
            navigator.clipboard.writeText(url).then(() => {{
                const orig = btn.innerText;
                btn.innerText = '✅ Copiato!';
                btn.style.borderColor = '#22c55e'; btn.style.color = '#22c55e';
                setTimeout(() => {{ btn.innerText = orig; btn.style.borderColor = ''; btn.style.color = ''; }}, 2000);
            }}).catch(() => {{
                prompt('Copia questo link:', url);
            }});
        }};
    </script>
</body>
</html>
"""
    return html


def update_mode_configuration():
    """Imposta permanentemente la modalità privata in config/active_mode.json."""
    print("[5/5] Consolidamento configurazione in config/active_mode.json...")
    cfg = {
        "mode": "private",
        "private_token": PRIVATE_TOKEN,
        "private_config": {
            "target": "anno_3_viola",
            "cdl_id": 458,
            "anno_id": 1084,
            "curr_id": 1736,
            "apple_calendar_name": "UniSR Med3 - Linea Viola",
            "google_calendar_prefix": "UniSR Med3 Viola"
        },
        "switched_at": datetime.now(timezone.utc).isoformat()
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(" -> Modalità 'private' salvata con successo.")


def main():
    print("================================================================")
    print(" AVVIO PROCEDURA: SPEGNIMENTO PUBBLICO E ATTIVAZIONE PRIVATA    ")
    print("================================================================")
    
    # 1. Svuotamento feed pubblici
    purge_public_calendars()
    
    # 2. Scraping 3° anno Linea Viola
    lessons = fetch_viola_lessons()
    if not lessons:
        print("[AVVISO] Nessuna lezione estratta. Generazione feed con dati minimi di fallback.")
    
    # 3. Costruzione feed privati
    generate_private_feeds(lessons)
    
    # 4. Aggiornamento stato
    update_mode_configuration()

    print("\n================================================================")
    print(" OPERAZIONE COMPLETATA CON SUCCESSO!                           ")
    print("================================================================")
    print(f"Directory privata creata: dist/{PRIVATE_TOKEN}/")
    print("Tutti i feed pubblici sono stati azzerati (silenzioso).")
    print("La dashboard per te e la tua compagna sarà accessibile su:")
    print(f" -> https://<tuo-username>.github.io/<nome-repo>/{PRIVATE_TOKEN}/")


if __name__ == "__main__":
    main()
