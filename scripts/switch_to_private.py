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
import http.client
import urllib.request
import html as html_lib
from datetime import datetime, timezone, date, timedelta
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, "dist")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "active_mode.json")
CACHE_PATH = os.path.join(BASE_DIR, "config", "orario_cache.json")

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


def sanitize_input(text, max_length=150):
    if not text:
        return ""
    text = re.sub(r'https?://\S+|www\.\S+', '[LINK RIMOSSO]', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]*>', '', text)
    return text[:max_length].strip()


COMPOUND_SURNAMES = (
    'DE ', 'DI ', 'DEL ', 'DELLA ', 'DELLO ', 'DEGLI ',
    'DAL ', 'DALLA ', 'LO ', 'LA ', 'MC ', 'MAC ',
    'VAN ', 'VON ', 'SAN ', 'SANT ', 'CAMISANI '
)


def format_docente_name(nome, cognome):
    nome = (nome or "").strip()
    cognome = (cognome or "").strip()
    if not cognome:
        return nome.title()
    
    iniziale = f"{nome[0].upper()}." if nome else ""
    cognome_fmt = " ".join([w.capitalize() for w in cognome.split()])
    cognome_fmt = re.sub(r"([a-zA-Z]')([a-zA-Z])", lambda m: m.group(1) + m.group(2).upper(), cognome_fmt)
    
    if iniziale:
        return f"{iniziale} {cognome_fmt}"
    return cognome_fmt


def format_orario_docente(raw_doc):
    """Converte 'COGNOME NOME' da orario.unisr.it in 'N. Cognome'."""
    s = " ".join((raw_doc or "").strip().upper().split())
    if not s:
        return ""
    if s == "NACLERO ASSUNTA":
        s = "NACLERIO ASSUNTA"
    words = s.split(" ")
    if len(words) == 1:
        return words[0].capitalize()
    if any(s.startswith(p) for p in COMPOUND_SURNAMES) and len(words) >= 3:
        cognome = f"{words[0]} {words[1]}"
        nome = " ".join(words[2:])
    else:
        cognome = words[0]
        nome = " ".join(words[1:])
    return format_docente_name(nome, cognome)


def get_activity_type_info(raw_title):
    raw_title = html_lib.unescape(raw_title)
    low = raw_title.lower()
    if " - apr" in low or " - apro" in low or "attività professionalizzanti" in low or "attivita professionalizzanti" in low:
        return "Attività Pratica", "APR"
    elif " - ese" in low or "esercitazion" in low:
        return "Esercitazione", "ESE"
    elif " - tir" in low or "tirocinio" in low:
        return "Tirocinio", "TIR"
    elif low.startswith("esame:"):
        return "Esame", "ESA"
    elif " - lez" in low or " - lez_d" in low or low.startswith("lezione:"):
        return "Lezione", "LEZ"
    return "Lezione", "LEZ"


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


def load_orario_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Warning] Impossibile leggere {CACHE_PATH}: {e}")
    return {}


def save_orario_cache(cache_data):
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception as e:
        print(f"[Warning] Impossibile salvare {CACHE_PATH}: {e}")


def parse_orario_day_html(body, date_dash):
    """Estrae le lezioni di Medicina 3 (Linea Viola + Elettivi) dall'HTML giornaliero di orario.unisr.it."""
    day_lessons = []
    seen = set()
    trs = re.split(r'<tr[^>]*>', body, flags=re.I)

    current_sede = ""
    current_aula = ""
    current_piano = ""

    for tr in trs:
        if "Corso di Laurea" in tr and "anno" in tr and "#C0C0C0" in tr:
            m_b = re.search(
                r'<font[^>]*color=#049AD9[^>]*>(.*?)</font>\s*-\s*<font[^>]*><b>(.*?)</b></font>\s*(?:\((.*?)\))?',
                tr,
                re.I | re.S
            )
            if m_b:
                current_sede = m_b.group(1).strip()
                raw_room = m_b.group(2).strip()
                current_aula = re.sub(r'^Aula\s+', '', raw_room, flags=re.I).strip()
                current_piano = (m_b.group(3) or "").strip()
        elif "Lezione:" in tr or "Esame:" in tr:
            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.I | re.S)
            if len(tds) < 4:
                continue
            clean_cell = lambda s: re.sub(r'<[^>]+>', '', s).replace('&nbsp;', ' ').replace('\xa0', ' ').strip()
            orario = clean_cell(tds[0])
            attivita = clean_cell(tds[1])
            cdl = clean_cell(tds[2])
            anno = clean_cell(tds[3])

            if anno != "3" or "-" not in orario:
                continue

            is_viola = "LINEA VIOLA" in attivita.upper()
            is_elettivo = (
                not is_viola
                and "LINEA" not in attivita.upper()
                and cdl == "Corso di Laurea magistrale in Medicina e Chirurgia"
            )

            if not (is_viola or is_elettivo):
                continue

            ora_ini, ora_fine = [x.strip() for x in orario.split("-", 1)]
            m_act = re.match(r'^(Lezione|Esame):\s*(.*?)\s*\(docente:\s*(.*?)\)\s*$', attivita, re.I)
            if m_act:
                prefix_type = m_act.group(1).capitalize()
                subj_raw = m_act.group(2).strip()
                doc_raw = m_act.group(3).strip()
            else:
                prefix_type = "Lezione"
                subj_raw = re.sub(r'^(Lezione|Esame):\s*', '', attivita, flags=re.I).strip()
                doc_raw = ""

            subj_clean = re.sub(r'\s*\(LINEA\s+VIOLA\)\s*', '', subj_raw, flags=re.I).strip()
            doc_fmt = format_orario_docente(doc_raw)
            nomi_docenti = [doc_fmt] if doc_fmt else []

            titolo_norm = f"{prefix_type}: {subj_clean}"
            if is_elettivo:
                titolo_norm += " - Corso Elettivo"

            key = (date_dash, ora_ini, ora_fine, subj_clean, current_sede, current_aula)
            if key in seen:
                continue
            seen.add(key)

            day_lessons.append({
                "id": "",
                "date": date_dash,
                "ora_inizio": ora_ini,
                "ora_fine": ora_fine,
                "titolo": titolo_norm,
                "aula": current_aula,
                "sede": current_sede,
                "piano": current_piano,
                "docenti": nomi_docenti,
                "elettivo": is_elettivo
            })

    return day_lessons


def merge_contiguous_lessons(lessons):
    """Fonde slot contigui (es. 08:30-10:30 + 10:30-12:30) con stessa data, materia, aula e docente."""
    if not lessons:
        return []

    def sort_for_merge(x):
        d, m, y = x["date"].split("-")
        return (f"{y}{m}{d}", x.get("sede", ""), x.get("aula", ""), x["titolo"], x["ora_inizio"])

    sorted_l = sorted(lessons, key=sort_for_merge)
    merged = [dict(sorted_l[0])]

    for curr in sorted_l[1:]:
        prev = merged[-1]
        if (
            prev["date"] == curr["date"]
            and prev["titolo"] == curr["titolo"]
            and prev.get("sede") == curr.get("sede")
            and prev.get("aula") == curr.get("aula")
            and prev.get("docenti") == curr.get("docenti")
            and prev["ora_fine"] == curr["ora_inizio"]
        ):
            prev["ora_fine"] = curr["ora_fine"]
        else:
            merged.append(dict(curr))

    def final_sort_key(x):
        d, m, y = x["date"].split("-")
        return f"{y}{m}{d}_{x['ora_inizio']}_{x['titolo']}"

    merged.sort(key=final_sort_key)
    return merged


def fetch_viola_lessons():
    """Estrae le lezioni del 3° Anno Linea Viola (+ Elettivi) da orario.unisr.it con cache incrementale e Keep-Alive."""
    print("[2/5] Interrogazione orario.unisr.it (Medicina 3 - Linea Viola + Elettivi)...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    cache = load_orario_cache()
    today = datetime.now(timezone.utc).date()

    start_d = date(2026, 9, 21)
    end_d = date(2027, 1, 23)

    weekdays = []
    curr = start_d
    while curr <= end_d:
        if curr.weekday() < 5:
            if not (date(2026, 12, 23) <= curr <= date(2027, 1, 6)):
                weekdays.append(curr)
        curr += timedelta(days=1)

    conn = None
    live_requests = 0
    live_success = 0
    cached_hits = 0

    for d_obj in weekdays:
        d_slash = d_obj.strftime("%d/%m/%Y")
        d_dash = d_obj.strftime("%d-%m-%Y")

        # Usa la cache per i giorni passati già storicizzati
        if d_obj < today and d_dash in cache:
            cached_hits += 1
            continue

        live_requests += 1
        path = f"/default.asp?ext=ok&data={d_slash}&CDS_ID=0&DAORA=0&ANNO_CORSO=3&id_palazzo=0&lezioni=ok&esami=ok"
        body = ""
        for attempt in range(3):
            try:
                if conn is None:
                    conn = http.client.HTTPSConnection("orario.unisr.it", context=ctx, timeout=15)
                conn.request("GET", path, headers={"User-Agent": "Mozilla/5.0", "Connection": "keep-alive"})
                resp = conn.getresponse()
                raw_bytes = resp.read()
                if resp.status == 200 and len(raw_bytes) > 5000:
                    body = raw_bytes.decode("latin-1", errors="replace")
                    live_success += 1
                    break
            except Exception as e:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = None
                if attempt == 2:
                    print(f"[Warning] Errore fetch {d_slash}: {e}")
                time.sleep(1)

        if body:
            cache[d_dash] = parse_orario_day_html(body, d_dash)

    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass

    if live_requests > 0 and live_success == 0:
        print("[ERRORE] Nessuna risposta valida da orario.unisr.it.")
        return []

    save_orario_cache(cache)

    raw_lessons = []
    for d_obj in weekdays:
        d_dash = d_obj.strftime("%d-%m-%Y")
        raw_lessons.extend(cache.get(d_dash, []))

    all_lessons = merge_contiguous_lessons(raw_lessons)
    print(
        f" -> Estratte {len(all_lessons)} lezioni totali "
        f"(da {cached_hits} giorni in cache + {live_success}/{live_requests} giorni live)."
    )
    return all_lessons


def clean_title(raw_title):
    raw_title = html_lib.unescape(raw_title)
    raw_title = sanitize_input(raw_title, max_length=200)

    clean = re.sub(r'^(Lezione|Esame):\s*', '', raw_title, flags=re.IGNORECASE)
    clean = re.sub(r'\s*\(LINEA\s+[^\)]+\)\s*', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s*-\s*Corso Elettivo.*$', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s*-\s*(LEZ(_D)?|ESE|APR(_[A-Z0-9]+)?|TIR|APRO).*$', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s*\[.*?\]', '', clean).strip()

    if clean.lower() in ("evento generico", "eventi generici"):
        clean = "Eventi generici"

    return clean


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

        base_subj = get_base_subject_name(summary)
        tipo_nome, tipo_tag = get_activity_type_info(l['titolo'])
        if tipo_tag:
            summary_with_tag = f"[{tipo_tag}] {summary.upper()}"
        else:
            summary_with_tag = summary.upper()

        location = ""
        if l.get('aula'):
            raw_aula = l['aula'].strip()
            if raw_aula.lower().startswith("aula"):
                location = raw_aula
            else:
                location = f"Aula {raw_aula}"

        desc_luogo_parts = []
        if l.get('sede'):
            raw_sede = l['sede'].strip()
            if raw_sede.lower().startswith("edificio"):
                desc_luogo_parts.append(raw_sede)
            else:
                desc_luogo_parts.append(f"Edificio {raw_sede}")
        if location:
            desc_luogo_parts.append(location)
        desc_luogo = ", ".join(desc_luogo_parts)

        desc_lines = [f"Materia: {base_subj}"]
        if tipo_nome:
            desc_lines.append(f"Tipo: {tipo_nome}")
        if l.get('docenti'):
            doc_label = "Docente" if len(l['docenti']) == 1 else "Docenti"
            desc_lines.append(f"{doc_label}: {', '.join(l['docenti'])}")
        if desc_luogo:
            desc_lines.append(f"Luogo: {desc_luogo}")
        desc_lines.append(f"Orario: {l['ora_inizio']} - {l['ora_fine']}")
        if "Eventi generici" in base_subj:
            desc_lines.append("Nota: Attività extra, assemblee, benvenuto matricole o altri eventi generici.")

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            f"DTSTART;TZID=Europe/Rome:{dtstart}",
            f"DTEND;TZID=Europe/Rome:{dtend}",
            f"SUMMARY:{escape_ical_text(summary_with_tag)}",
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
    valid_materie_files = set()
    for s_name, s_lessons in sorted(subjects.items()):
        slug = slugify(s_name)
        f_name = f"materia_{slug}.ics"
        valid_materie_files.add(f_name)
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

    for existing_f in os.listdir(materie_dir):
        if existing_f.endswith(".ics") and existing_f not in valid_materie_files:
            os.remove(os.path.join(materie_dir, existing_f))
            print(f" -> Rimosso feed materia obsoleto: {existing_f}")

    # 3. Feed separati per elettivi
    elettivi_subjects = defaultdict(list)
    for l in electives:
        s = get_base_subject_name(clean_title(l['titolo']))
        elettivi_subjects[s].append(l)

    elettivi_ui = []
    valid_elettivi_files = set()
    for e_name, e_lessons in sorted(elettivi_subjects.items()):
        slug = slugify(e_name)
        f_name = f"elettivo_{slug}.ics"
        valid_elettivi_files.add(f_name)
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

    for existing_f in os.listdir(elettivi_dir):
        if existing_f.endswith(".ics") and existing_f not in valid_elettivi_files:
            os.remove(os.path.join(elettivi_dir, existing_f))
            print(f" -> Rimosso feed elettivo obsoleto: {existing_f}")

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
        if (elettivi.length > 0) {{
            document.getElementById('elettivi-grid').innerHTML = elettivi.map(buildCard).join('');
        }} else {{
            document.getElementById('elettivi-grid').innerHTML = '<p style="color:var(--text-muted); font-size:0.95rem;">Nessun corso elettivo rilevato per questa linea.</p>';
        }}

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
    apple_file = os.path.join(PRIVATE_DIR, "apple_linea_viola.ics")
    has_existing_feeds = os.path.exists(apple_file) and os.path.getsize(apple_file) > 1000

    if not lessons and has_existing_feeds:
        print("[CIRCUIT BREAKER] Nessuna lezione estratta da EasyCourse ma i feed privati esistono gia. Preservo i feed esistenti.")
    else:
        # 3. Costruzione feed privati
        generate_private_feeds(lessons)
    
    # 4. Aggiornamento stato
    update_mode_configuration()

    # 5. Notifiche corsi monitorati
    if lessons:
        try:
            src_dir = os.path.join(BASE_DIR, "src")
            if src_dir not in sys.path:
                sys.path.insert(0, src_dir)
            from notifications import check_and_notify_watched_courses
            print("\n=== Verifica Corsi Monitorati (Notifiche Telegram) ===")
            check_and_notify_watched_courses(lessons)
        except Exception as e:
            print(f"[Warning] Controllo notifiche Telegram fallito: {e}")

    print("\n================================================================")
    print(" OPERAZIONE COMPLETATA CON SUCCESSO!                           ")
    print("================================================================")
    print(f"Directory privata creata: dist/{PRIVATE_TOKEN}/")
    print("Tutti i feed pubblici sono stati azzerati (silenzioso).")
    print("La dashboard per te e la tua compagna sarà accessibile su:")
    print(f" -> https://<tuo-username>.github.io/<nome-repo>/{PRIVATE_TOKEN}/")


if __name__ == "__main__":
    main()
