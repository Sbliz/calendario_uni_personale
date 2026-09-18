#!/usr/bin/env python3
"""
Sincronizzatore Calendario Accademico UNISR
Medicina e Chirurgia 3 [CLMMC-C] - Linea Viola (S1)

Genera:
- Calendari Curricolari Principali:
  1. medicina3_ios.ics                -> Feed completo per Apple Calendar (iOS)
  2. medicina3_patologia.ics          -> Google Calendar (Colore: Banana)
  3. medicina3_med_laboratorio.ics    -> Google Calendar (Colore: Amethyst)
  4. medicina3_preparedness.ics       -> Google Calendar (Colore: Cherry Blossom)
  5. medicina3_microbiologia.ics      -> Google Calendar (Colore: Eucalyptus)

- Calendari Dedicati per ciascun Corso Elettivo (Colore Google Calendar: Tangerine / Arancione):
  6. elettivo_cyber_humanities.ics
  7. elettivo_imaging_sistema_nervoso.ics
  8. elettivo_ricerche_bibliografiche.ics
  9. elettivo_semeiotica_chirurgia.ics
  10. elettivo_teleneurofisiologia.ics
  11. elettivo_urgenze_chirurgia_vascolare.ics
"""

import os
import re
import ssl
import json
import hashlib
import unicodedata
import urllib.request
from datetime import datetime, timezone
from collections import defaultdict

URL_EASYCOURSE = (
    "https://easycourse.unisr.it/easycourse-new/pubblicazioni-riservate/standardGrid/"
    "figlia-4/2026-2027/s1/riservato?"
    "catena=S1&ricercaIndex=Corso+di+studi&CorsoDiStudio=458&annoCorso=1084&curriculum=1736&settimana=all"
)

DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")


def fetch_schedule_html():
    """Scarica il codice HTML dell'intero semestre da EasyCourse."""
    print("Collegamento a EasyCourse UNISR per il semestre completo...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        URL_EASYCOURSE,
        headers={
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        }
    )
    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
        return resp.read().decode('utf-8', errors='ignore')


def extract_lessons_from_html(html):
    """
    Estrae le lezioni isolando ciascun 'giorno-container'.
    Estrae SOLO dall'interno del contenitore 'lezioni-giornaliere'.
    """
    giorno_blocks = re.findall(
        r'<div[^>]*class="giorno-container\s*([^"]*)"[^>]*>(.*?)(?=<div[^>]*class="giorno-container|<div[^>]*class="easy-ph|<!-- ================= DESKTOP|$)',
        html,
        re.DOTALL
    )
    print(f"Blocchi giorno-container isolati: {len(giorno_blocks)}")

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

            # Parsing docenti
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
    return all_lessons


def clean_title(raw_title):
    """Pulisce il titolo per una visualizzazione ordinata nel calendario."""
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


def get_elective_course_name(full_title):
    """Estrae il nome univoco della materia per un corso elettivo."""
    # Es: "Cyber-Humanities - LEZ - Corso Elettivo" -> "Cyber-Humanities"
    m = re.match(r'^(.*?)\s*-\s*(?:LEZ|ESE|LEZ_D|APR)', full_title)
    if m:
        return m.group(1).strip()
    return full_title.split('[')[0].strip()


def slugify(text):
    """Genera uno slug pulito per il nome del file .ics."""
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '_', text)


def generate_uid(lesson):
    """Genera un UID deterministico e persistente per ciascuna sessione."""
    unique_key = f"{lesson['date']}_{lesson['ora_inizio']}_{lesson['ora_fine']}_{lesson['titolo']}_{lesson['sede']}_{lesson['aula']}"
    h = hashlib.sha256(unique_key.encode('utf-8')).hexdigest()[:16]
    return f"unisr-med3-{h}@easycourse.unisr.it"


def format_ical_dt(date_str, time_str):
    """Converte 'DD-MM-YYYY' e 'HH:MM' in 'YYYYMMDDTHHMMSS'."""
    day, month, year = date_str.split('-')
    hour, minute = time_str.split(':')
    return f"{year}{month}{day}T{hour}{minute}00"


def escape_ical_text(text):
    """Escape per caratteri speciali standard RFC 5545."""
    if not text:
        return ""
    text = text.replace('\\', '\\\\')
    text = text.replace(';', '\\;')
    text = text.replace(',', '\\,')
    text = text.replace('\n', '\\n')
    return text


def build_ics_calendar(calendar_name, lessons, description=""):
    """Costruisce il file iCalendar RFC 5545 conforme."""
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//UniSR//Calendario Medicina 3 Linea Viola//IT",
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
        if l['sede']:
            loc_parts.append(f"Edificio {l['sede']}")
        if l['aula']:
            loc_parts.append(f"Aula {l['aula']}")
        location = ", ".join(loc_parts)

        desc_lines = [
            f"Insegnamento: {l['titolo']}",
        ]
        if l['docenti']:
            desc_lines.append(f"Docenti: {', '.join(l['docenti'])}")
        if location:
            desc_lines.append(f"Luogo: {location}")
        desc_lines.append(f"Orario: {l['ora_inizio']} - {l['ora_fine']}")
        desc_lines.append("Fonte: EasyCourse UniSR (Sincronizzato)")

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


def generate_index_html(curricular_feeds, elective_feeds):
    """Genera la landing page HTML organizzata in sezioni."""
    
    def render_cards(feeds):
        html_cards = []
        for f in feeds:
            badge_style = f"background-color: {f['badge_bg']}; color: {f['badge_fg']}; border: 1px solid {f['badge_border']};"
            html_cards.append(f"""
            <div class="card">
                <div class="card-header">
                    <span class="badge" style="{badge_style}">{f['color_name']}</span>
                    <h3>{f['title']}</h3>
                </div>
                <p class="card-desc">{f['description']}</p>
                <p class="card-meta"><b>{f['count']}</b> sessioni in calendario</p>
                <div class="actions">
                    <a href="webcal://{{HOST_PATH}}/{f['filename']}" class="btn btn-ios">
                         Sottoscrivi su iOS
                    </a>
                    <button onclick="copyFeedUrl('{f['filename']}', this)" class="btn btn-copy">
                        📋 Copia Link Google Calendar
                    </button>
                </div>
            </div>""")
        return "\n".join(html_cards)

    curr_html = render_cards(curricular_feeds)
    elett_html = render_cards(elective_feeds)
    update_time_str = datetime.now().strftime('%d/%m/%Y %H:%M')

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sincronizzazione Calendario UniSR - Medicina 3</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --surface-hover: #334155;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #38bdf8;
            --border: #334155;
            --orange: #fb923c;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            padding: 2rem 1rem;
            line-height: 1.5;
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
        }}
        header {{
            text-align: center;
            margin-bottom: 2.5rem;
        }}
        h1 {{
            font-size: 2.1rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: #fff;
        }}
        .subtitle {{
            color: var(--text-muted);
            font-size: 1.15rem;
        }}
        .last-update {{
            display: inline-block;
            margin-top: 0.75rem;
            font-size: 0.85rem;
            background: #0ea5e922;
            color: #38bdf8;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
        }}
        .section-title {{
            font-size: 1.4rem;
            font-weight: 600;
            margin: 2rem 0 1rem 0;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2.5rem;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}
        .card:hover {{
            transform: translateY(-2px);
            border-color: #475569;
        }}
        .card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.75rem;
            gap: 0.5rem;
        }}
        .card-header h3 {{
            font-size: 1.1rem;
            font-weight: 600;
            flex-grow: 1;
        }}
        .badge {{
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
            text-transform: uppercase;
            white-space: nowrap;
        }}
        .card-desc {{
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-bottom: 0.75rem;
        }}
        .card-meta {{
            font-size: 0.85rem;
            color: #cbd5e1;
            margin-bottom: 1rem;
        }}
        .actions {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}
        .btn {{
            display: block;
            text-align: center;
            padding: 0.6rem 0.75rem;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            border: none;
            transition: opacity 0.2s;
        }}
        .btn:hover {{ opacity: 0.9; }}
        .btn-ios {{
            background: #0284c7;
            color: white;
        }}
        .btn-copy {{
            background: var(--surface-hover);
            color: #e2e8f0;
            border: 1px solid var(--border);
        }}
        .instructions {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
        }}
        .instructions h2 {{
            font-size: 1.25rem;
            margin-bottom: 1rem;
            color: #fff;
        }}
        .instructions ol {{
            padding-left: 1.25rem;
            color: var(--text-muted);
        }}
        .instructions li {{
            margin-bottom: 0.5rem;
        }}
        .instructions ul {{
            margin-top: 0.5rem;
            padding-left: 1.25rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Calendario Medicina e Chirurgia 3</h1>
            <p class="subtitle">UniSR - Canale [CLMMC-C] Linea Viola (S1)</p>
            <span class="last-update">Ultimo aggiornamento automatico: {update_time_str}</span>
        </header>

        <h2 class="section-title">📚 Corsi Obbligatori Curricolari</h2>
        <div class="grid">
            {curr_html}
        </div>

        <h2 class="section-title">🎯 Corsi Elettivi (A scelta dello studente - Colore: Arancione)</h2>
        <p style="color:var(--text-muted); margin-top:-0.5rem; margin-bottom:1rem; font-size:0.95rem;">
            Sottoscrivi solo i corsi elettivi che hai effettivamente scelto di frequentare.
        </p>
        <div class="grid">
            {elett_html}
        </div>

        <div class="instructions">
            <h2>📱 Guida Rapida alla Sottoscrizione</h2>
            <ol>
                <li><b>Su iPhone / iPad (iOS):</b> Clicca sul pulsante azzurro <i>"Sottoscrivi su iOS"</i> del calendario che desideri aggiungere. iOS aprirà l'app Calendario e completerà l'iscrizione.</li>
                <li><b>Su Google Calendar:</b>
                    <ul>
                        <li>Clicca su <i>"Copia Link Google Calendar"</i> accanto alla materia desiderata.</li>
                        <li>Apri <a href="https://calendar.google.com" target="_blank" style="color:var(--primary);">Google Calendar</a> da browser.</li>
                        <li>Nella barra laterale a sinistra, accanto ad <b>"Altri calendari"</b>, clicca su <b>+</b> &gt; <b>Da URL</b>.</li>
                        <li>Incolla l'URL e clicca su <i>"Aggiungi calendario"</i>.</li>
                        <li>Dal menu a tre puntini (⋮) del calendario aggiunto, assegna il colore corrispondente:
                            <b>Banana</b> (Patologia), <b>Amethyst</b> (Med Lab), <b>Cherry Blossom</b> (Preparedness), <b>Eucalyptus</b> (Microbiologia), <b>Tangerine / Arancione</b> (Corsi Elettivi).</li>
                    </ul>
                </li>
            </ol>
        </div>
    </div>

    <script>
        const hostPath = window.location.href.replace(/\\/index\\.html$/, '').replace(/\\/$/, '');
        document.querySelectorAll('a.btn-ios').forEach(a => {{
            const currentHref = a.getAttribute('href');
            a.setAttribute('href', currentHref.replace('{{HOST_PATH}}', hostPath.replace(/^https?:\\/\\//, '')));
        }});

        function copyFeedUrl(filename, btn) {{
            const url = hostPath + '/' + filename + '?v=2';
            navigator.clipboard.writeText(url).then(() => {{
                const orig = btn.innerText;
                btn.innerText = '✅ Link Copiato!';
                btn.style.borderColor = '#22c55e';
                btn.style.color = '#22c55e';
                setTimeout(() => {{
                    btn.innerText = orig;
                    btn.style.borderColor = '';
                    btn.style.color = '';
                }}, 2000);
            }}).catch(() => {{
                prompt('Copia questo link:', url);
            }});
        }}
    </script>
</body>
</html>
"""


def main():
    print("=== Avvio Sincronizzatore Calendario UniSR ===")
    os.makedirs(DIST_DIR, exist_ok=True)

    # 1. Download HTML
    raw_html = fetch_schedule_html()
    print(f"HTML scaricato con successo ({len(raw_html)} bytes)")

    # 2. Parsing dai blocchi giorno-container isolati
    all_lessons = extract_lessons_from_html(raw_html)
    print(f"Sessioni uniche estratte: {len(all_lessons)}")

    # 3. Separazione Curricolari vs Corsi Elettivi
    curricular = [l for l in all_lessons if not l['elettivo']]
    electives = [l for l in all_lessons if l['elettivo']]

    print(f"Lezioni Curricolari Obbligatorie: {len(curricular)}")
    print(f"Lezioni Elettive Totali: {len(electives)}")

    # 4. Raggruppamento Materie Curricolari
    groups = {
        'patologia': [],
        'med_laboratorio': [],
        'preparedness': [],
        'microbiologia': [],
        'altre': []
    }

    for l in curricular:
        t = l['titolo'].lower()
        if 'patologia' in t and 'laboratorio' not in t:
            groups['patologia'].append(l)
        elif 'laboratorio' in t:
            groups['med_laboratorio'].append(l)
        elif 'preparedness' in t:
            groups['preparedness'].append(l)
        elif 'microbiologia' in t:
            groups['microbiologia'].append(l)
        else:
            groups['altre'].append(l)

    # 5. Raggruppamento dei Corsi Elettivi per singolo corso
    electives_by_course = defaultdict(list)
    for l in electives:
        cname = get_elective_course_name(l['titolo'])
        electives_by_course[cname].append(l)

    print(f"Corsi Elettivi distinti rilevati: {len(electives_by_course)}")

    # 6. Definizione Feed Curricolari
    curricular_feeds = [
        {
            'filename': 'medicina3_ios.ics',
            'title': 'UniSR Medicina 3 [Completo]',
            'description': 'Calendario accademico completo Medicina 3 (CLMMC-C Linea Viola) per iOS',
            'lessons': curricular,
            'badge_bg': '#38bdf822',
            'badge_fg': '#38bdf8',
            'badge_border': '#38bdf8',
            'color_name': 'iOS Completo',
            'count': len(curricular)
        },
        {
            'filename': 'medicina3_patologia.ics',
            'title': 'Patologia',
            'description': 'Patologia [C0019] - Canale Viola',
            'lessons': groups['patologia'],
            'badge_bg': '#fef08a22',
            'badge_fg': '#facc15',
            'badge_border': '#facc15',
            'color_name': 'GCal: Banana',
            'count': len(groups['patologia'])
        },
        {
            'filename': 'medicina3_med_laboratorio.ics',
            'title': 'Medicina di Laboratorio',
            'description': 'Medicina di Laboratorio [C0020] e Attività Professionalizzanti [C0055]',
            'lessons': groups['med_laboratorio'],
            'badge_bg': '#c084fc22',
            'badge_fg': '#c084fc',
            'badge_border': '#c084fc',
            'color_name': 'GCal: Amethyst',
            'count': len(groups['med_laboratorio'])
        },
        {
            'filename': 'medicina3_preparedness.ics',
            'title': 'Preparedness',
            'description': 'Preparedness in Medicina: dal Quotidiano allo Straordinario [C0025]',
            'lessons': groups['preparedness'],
            'badge_bg': '#f472b622',
            'badge_fg': '#f472b6',
            'badge_border': '#f472b6',
            'color_name': 'GCal: Cherry Blossom',
            'count': len(groups['preparedness'])
        },
        {
            'filename': 'medicina3_microbiologia.ics',
            'title': 'Microbiologia Clinica',
            'description': 'Microbiologia e Microbiologia Clinica [C0016]',
            'lessons': groups['microbiologia'],
            'badge_bg': '#4ade8022',
            'badge_fg': '#4ade80',
            'badge_border': '#4ade80',
            'color_name': 'GCal: Eucalyptus',
            'count': len(groups['microbiologia'])
        }
    ]

    # 7. Definizione Feed per ciascun Corso Elettivo (Colore Arancione)
    elective_feeds = []
    # Mappa nomi corti per i file
    slug_map = {
        'Cyber-Humanities': 'elettivo_cyber_humanities.ics',
        'Imaging morfologico e funzionale del sistema nervoso': 'elettivo_imaging_sistema_nervoso.ics',
        'Ricerche bibliografiche': 'elettivo_ricerche_bibliografiche.ics',
        'Semeiotica applicata alla chirurgia: dal segno obiettivo alla scelta operatoria': 'elettivo_semeiotica_chirurgia.ics',
        'Tele-neuro fisiologia, neuromodulazione e tecnologie digitali': 'elettivo_teleneurofisiologia.ics',
        'Urgenze ed emergenze in chirurgia vascolare: tempo di pace e tempo di guerra': 'elettivo_urgenze_chirurgia_vascolare.ics',
    }

    for cname, c_lessons in sorted(electives_by_course.items()):
        fname = slug_map.get(cname, f"elettivo_{slugify(cname)}.ics")
        elective_feeds.append({
            'filename': fname,
            'title': f"Elettivo: {cname}",
            'description': f"Corso Elettivo: {cname} - Medicina 3",
            'lessons': c_lessons,
            'badge_bg': '#fb923c22',
            'badge_fg': '#fb923c',
            'badge_border': '#fb923c',
            'color_name': 'GCal: Arancione',
            'count': len(c_lessons)
        })

    # Scrittura di tutti i file .ics
    all_feeds = curricular_feeds + elective_feeds
    for item in all_feeds:
        filepath = os.path.join(DIST_DIR, item['filename'])
        ics_content = build_ics_calendar(item['title'], item['lessons'], item['description'])
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(ics_content)
        print(f"Generato: {item['filename']} ({len(item['lessons'])} lezioni)")

    # 8. Generazione pagina HTML di sottoscrizione
    index_html = generate_index_html(curricular_feeds, elective_feeds)
    with open(os.path.join(DIST_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print("Generata pagina di sottoscrizione: dist/index.html")

    print("=== Sincronizzazione completata con successo ===")


if __name__ == "__main__":
    main()
