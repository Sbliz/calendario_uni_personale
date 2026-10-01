#!/usr/bin/env python3
"""
Sincronizzatore Calendario Accademico UNISR
Multicanale - Medicina e Chirurgia (Tutti gli anni, tutte le linee)
File monolitico auto-consistente per GitHub Actions.
"""

import os
import re
import ssl
import time
import json
import hashlib
import unicodedata
import urllib.request
import html
from datetime import datetime, timezone
from collections import defaultdict

DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")
ACRONIMI_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ACRONIMI.md")

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

MEDICINA_CONFIG = [
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia 2 [CLMMC-B]",
        "cdl_id": 456,
        "anno": 3,
        "anno_id": 1081,
        "linea_name": "PERCORSO COMUNE LINEA GIALLA",
        "linea_id": 1729,
        "slug_linea": "gialla",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia 2 [CLMMC-B]",
        "cdl_id": 456,
        "anno": 3,
        "anno_id": 1081,
        "linea_name": "PERCORSO COMUNE LINEA VERDE",
        "linea_id": 1730,
        "slug_linea": "verde",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia 2 [CLMMCB]",
        "cdl_id": 457,
        "anno": 1,
        "anno_id": 1082,
        "linea_name": "PERCORSO COMUNE LINEA GIALLA",
        "linea_id": 1731,
        "slug_linea": "gialla",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia 2 [CLMMCB]",
        "cdl_id": 457,
        "anno": 1,
        "anno_id": 1082,
        "linea_name": "PERCORSO COMUNE LINEA VERDE",
        "linea_id": 1732,
        "slug_linea": "verde",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia 2 [CLMMCB]",
        "cdl_id": 457,
        "anno": 2,
        "anno_id": 1083,
        "linea_name": "PERCORSO COMUNE LINEA GIALLA",
        "linea_id": 1733,
        "slug_linea": "gialla",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia 2 [CLMMCB]",
        "cdl_id": 457,
        "anno": 2,
        "anno_id": 1083,
        "linea_name": "PERCORSO COMUNE LINEA VERDE",
        "linea_id": 1734,
        "slug_linea": "verde",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia 3 [CLMMC-C]",
        "cdl_id": 458,
        "anno": 3,
        "anno_id": 1084,
        "linea_name": "PERCORSO COMUNE LINEA ROSSA",
        "linea_id": 1735,
        "slug_linea": "rossa",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia 3 [CLMMC-C]",
        "cdl_id": 458,
        "anno": 3,
        "anno_id": 1084,
        "linea_name": "PERCORSO COMUNE LINEA VIOLA",
        "linea_id": 1736,
        "slug_linea": "viola",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia 3 [CLMMCC]",
        "cdl_id": 459,
        "anno": 1,
        "anno_id": 1085,
        "linea_name": "PERCORSO COMUNE LINEA ROSSA",
        "linea_id": 1737,
        "slug_linea": "rossa",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia 3 [CLMMCC]",
        "cdl_id": 459,
        "anno": 1,
        "anno_id": 1085,
        "linea_name": "PERCORSO COMUNE LINEA VIOLA",
        "linea_id": 1738,
        "slug_linea": "viola",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia 3 [CLMMCC]",
        "cdl_id": 459,
        "anno": 2,
        "anno_id": 1086,
        "linea_name": "PERCORSO COMUNE LINEA ROSSA",
        "linea_id": 1739,
        "slug_linea": "rossa",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia 3 [CLMMCC]",
        "cdl_id": 459,
        "anno": 2,
        "anno_id": 1086,
        "linea_name": "PERCORSO COMUNE LINEA VIOLA",
        "linea_id": 1740,
        "slug_linea": "viola",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMCA]",
        "cdl_id": 455,
        "anno": 1,
        "anno_id": 1079,
        "linea_name": "PERCORSO COMUNE LINEA AZZURRA",
        "linea_id": 1725,
        "slug_linea": "azzurra",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMCA]",
        "cdl_id": 455,
        "anno": 1,
        "anno_id": 1079,
        "linea_name": "PERCORSO COMUNE LINEA BIANCA",
        "linea_id": 1726,
        "slug_linea": "bianca",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMCA]",
        "cdl_id": 455,
        "anno": 2,
        "anno_id": 1080,
        "linea_name": "PERCORSO COMUNE LINEA AZZURRA",
        "linea_id": 1727,
        "slug_linea": "azzurra",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMCA]",
        "cdl_id": 455,
        "anno": 2,
        "anno_id": 1080,
        "linea_name": "PERCORSO COMUNE LINEA BIANCA",
        "linea_id": 1728,
        "slug_linea": "bianca",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 3,
        "anno_id": 1075,
        "linea_name": "PERCORSO COMUNE LINEA AZZURRA",
        "linea_id": 1709,
        "slug_linea": "azzurra",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 3,
        "anno_id": 1075,
        "linea_name": "PERCORSO COMUNE LINEA BIANCA",
        "linea_id": 1710,
        "slug_linea": "bianca",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 4,
        "anno_id": 1076,
        "linea_name": "PERCORSO COMUNE LINEA AZZURRA",
        "linea_id": 1711,
        "slug_linea": "azzurra",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 4,
        "anno_id": 1076,
        "linea_name": "PERCORSO COMUNE LINEA BIANCA",
        "linea_id": 1712,
        "slug_linea": "bianca",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 4,
        "anno_id": 1076,
        "linea_name": "PERCORSO COMUNE LINEA GIALLA",
        "linea_id": 1713,
        "slug_linea": "gialla",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 4,
        "anno_id": 1076,
        "linea_name": "PERCORSO COMUNE LINEA ROSSA",
        "linea_id": 1714,
        "slug_linea": "rossa",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 4,
        "anno_id": 1076,
        "linea_name": "PERCORSO COMUNE LINEA VERDE",
        "linea_id": 1715,
        "slug_linea": "verde",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 4,
        "anno_id": 1076,
        "linea_name": "PERCORSO COMUNE LINEA VIOLA",
        "linea_id": 1716,
        "slug_linea": "viola",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 5,
        "anno_id": 1077,
        "linea_name": "PERCORSO COMUNE LINEA AZZURRA",
        "linea_id": 1717,
        "slug_linea": "azzurra",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 5,
        "anno_id": 1077,
        "linea_name": "PERCORSO COMUNE LINEA BIANCA",
        "linea_id": 1718,
        "slug_linea": "bianca",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 5,
        "anno_id": 1077,
        "linea_name": "PERCORSO COMUNE LINEA GIALLA",
        "linea_id": 1719,
        "slug_linea": "gialla",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 5,
        "anno_id": 1077,
        "linea_name": "PERCORSO COMUNE LINEA VERDE",
        "linea_id": 1720,
        "slug_linea": "verde",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 6,
        "anno_id": 1078,
        "linea_name": "PERCORSO COMUNE LINEA AZZURRA",
        "linea_id": 1721,
        "slug_linea": "azzurra",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 6,
        "anno_id": 1078,
        "linea_name": "PERCORSO COMUNE LINEA BIANCA",
        "linea_id": 1722,
        "slug_linea": "bianca",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 6,
        "anno_id": 1078,
        "linea_name": "PERCORSO COMUNE LINEA GIALLA",
        "linea_id": 1723,
        "slug_linea": "gialla",
        "is_imd": False
    },
    {
        "cdl_name": "Corso di Laurea magistrale in Medicina e Chirurgia [CLMMC]",
        "cdl_id": 454,
        "anno": 6,
        "anno_id": 1078,
        "linea_name": "PERCORSO COMUNE LINEA VERDE",
        "linea_id": 1724,
        "slug_linea": "verde",
        "is_imd": False
    },
    {
        "cdl_name": "International MD Program Corso di Laurea Magistrale in Medicina e Chirurgia [CLIMDP]",
        "cdl_id": 460,
        "anno": 1,
        "anno_id": 1087,
        "linea_name": "PERCORSO COMUNE",
        "linea_id": 1741,
        "slug_linea": "comune",
        "is_imd": True
    },
    {
        "cdl_name": "International MD Program Corso di Laurea Magistrale in Medicina e Chirurgia [CLIMDP]",
        "cdl_id": 460,
        "anno": 2,
        "anno_id": 1088,
        "linea_name": "PERCORSO COMUNE",
        "linea_id": 1742,
        "slug_linea": "comune",
        "is_imd": True
    },
    {
        "cdl_name": "International MD Program Corso di Laurea Magistrale in Medicina e Chirurgia [CLMMCI]",
        "cdl_id": 461,
        "anno": 3,
        "anno_id": 1089,
        "linea_name": "PERCORSO COMUNE",
        "linea_id": 1743,
        "slug_linea": "comune",
        "is_imd": True
    },
    {
        "cdl_name": "International MD Program Corso di Laurea Magistrale in Medicina e Chirurgia [CLMMCI]",
        "cdl_id": 461,
        "anno": 4,
        "anno_id": 1090,
        "linea_name": "PERCORSO COMUNE",
        "linea_id": 1744,
        "slug_linea": "comune",
        "is_imd": True
    },
    {
        "cdl_name": "International MD Program Corso di Laurea Magistrale in Medicina e Chirurgia [CLMMCI]",
        "cdl_id": 461,
        "anno": 5,
        "anno_id": 1091,
        "linea_name": "PERCORSO COMUNE",
        "linea_id": 1745,
        "slug_linea": "comune",
        "is_imd": True
    },
    {
        "cdl_name": "International MD Program Corso di Laurea Magistrale in Medicina e Chirurgia [CLMMCI]",
        "cdl_id": 461,
        "anno": 6,
        "anno_id": 1092,
        "linea_name": "PERCORSO COMUNE",
        "linea_id": 1746,
        "slug_linea": "comune",
        "is_imd": True
    },
]


def get_color_for_subject(subject_name):
    """Assegna un colore della palette in base all'hash del nome (deterministico)."""
    h = int(hashlib.md5(subject_name.encode('utf-8')).hexdigest(), 16)
    return PALETTE[h % len(PALETTE)]


def fetch_schedule_html(cdl_id, anno_id, curr_id):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

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
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=40) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            if attempt == 2:
                print(f"Errore download {cdl_id}/{anno_id}/{curr_id}: {e}")
                return ""
            time.sleep(2)


def extract_lessons_from_html(html):
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
            titolo = html.unescape(get_attr("titolo"))
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
    return all_lessons


ACRONYMS_MAP = {}

def load_acronyms_map(md_file=ACRONIMI_FILE):
    """
    Carica la mappatura degli acronimi dal file markdown ACRONIMI.md.
    Permette all'utente di personalizzare gli acronimi modificando direttamente il file .md.
    """
    global ACRONYMS_MAP
    if not os.path.exists(md_file):
        print(f"[Avviso] File acronimi non trovato: {md_file}")
        return {}
    
    mapping = {}
    try:
        with open(md_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("|") or not line.endswith("|"):
                    continue
                cols = [c.strip() for c in line.split("|")[1:-1]]
                if len(cols) >= 2:
                    subject, abbr = cols[0], cols[1]
                    if not subject or not abbr or "---" in subject or "materia" in subject.lower():
                        continue
                    clean_subj = html.unescape(subject).strip()
                    mapping[clean_subj.lower()] = abbr.strip().upper()
        print(f"[Acronimi] Caricati {len(mapping)} acronimi dal file {os.path.basename(md_file)}")
    except Exception as e:
        print(f"[Errore] Impossibile leggere {md_file}: {e}")
        
    ACRONYMS_MAP = mapping
    return mapping


def get_abbreviation(name):
    """
    Restituisce l'acronimo per la materia specificata.
    1. Cerca prima nel dizionario caricato dal file ACRONIMI.md
    2. Cerca corrispondenze parziali / parole chiave nel file ACRONIMI.md
    3. Genera una sigla euristica automatica come fallback per corsi futuri non ancora censiti.
    """
    if not name:
        return "GEN"
        
    global ACRONYMS_MAP
    if not ACRONYMS_MAP:
        load_acronyms_map()
        
    norm = html.unescape(name).strip().lower()
    
    # 1. Corrispondenza esatta nella tabella ACRONIMI.md
    if norm in ACRONYMS_MAP:
        return ACRONYMS_MAP[norm]
        
    # 2. Corrispondenza parziale (sottostringa o parola chiave presente nel file)
    for k, v in ACRONYMS_MAP.items():
        if k and (k in norm or norm in k):
            return v
            
    # 3. Fallback dinamico
    name_upper = html.unescape(name).upper()
    words = re.findall(r'[A-ZÀ-ÖØ-Þ]+', name_upper)
    stopwords = {"DI", "E", "IN", "DEL", "DELLA", "DELLO", "DEI", "DELLE", "DA", "A", "I", "II", "III", "IV", "V", "VI", "PER", "CON"}
    words = [w for w in words if w not in stopwords]
    
    if not words:
        return re.sub(r'[^A-Z0-9]', '', name_upper)[:4] or "GEN"
        
    if len(words) == 1:
        return words[0][:4]
    else:
        return words[0][:4] + words[1][:3]


def clean_title(raw_title):
    raw_title = html.unescape(raw_title)
    tipo = ""
    if " - LEZ" in raw_title or " - LEZ_D" in raw_title:
        tipo = "Lezione"
    elif " - ESE" in raw_title:
        tipo = "Esercitazione"
    elif " - APR" in raw_title or " - TIR" in raw_title or " - APRO" in raw_title:
        tipo = "Attività Pratica"
    
    clean = re.sub(r'\s*-\s*Corso Elettivo.*$', '', raw_title, flags=re.IGNORECASE)
    clean = re.sub(r'\s*-\s*(LEZ(_D)?|ESE|APR(_[A-Z0-9]+)?|TIR|APRO).*$', '', clean, flags=re.IGNORECASE)
    
    # Se dopo la rimozione dei tipi rimane una struttura 'NomeInsegnamento - ModuloCanale',
    # estraiamo il nome principale dell'insegnamento per evitare duplicati come 'Semeiotica - Semeiotica 2'
    parts = re.split(r'\s+-\s+', clean)
    base_name = parts[0].strip()
    base_name = re.sub(r'\s*\[.*?\]', '', base_name).strip()
    
    if base_name.lower() in ("evento generico", "eventi generici"):
        base_name = "Eventi generici"
        
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
    text = text.replace('\\', '\\\\')
    text = text.replace(';', '\\;')
    text = text.replace(',', '\\,')
    text = text.replace('\n', '\\n')
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
        abbr = get_abbreviation(base_subj)
        summary_with_abbr = f"[{abbr}] {summary}"

        loc_parts = []
        if l['sede']: loc_parts.append(f"Edificio {l['sede']}")
        if l['aula']: loc_parts.append(f"Aula {l['aula']}")
        location = ", ".join(loc_parts)

        desc_lines = [f"Materia: {base_subj}", f"Dettaglio: {l['titolo']}"]
        if "Eventi generici" in base_subj:
            desc_lines.append("Nota: Attività extra, assemblee, benvenuto matricole o altri eventi generici.")
            
        if l['docenti']: desc_lines.append(f"Docenti: {', '.join(l['docenti'])}")
        if location: desc_lines.append(f"Luogo: {location}")
        desc_lines.append(f"Orario: {l['ora_inizio']} - {l['ora_fine']}")
        desc_lines.append("Fonte: EasyCourse UniSR (Sincronizzato)")

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            f"DTSTART;TZID=Europe/Rome:{dtstart}",
            f"DTEND;TZID=Europe/Rome:{dtend}",
            f"SUMMARY:{escape_ical_text(summary_with_abbr)}",
            f"LOCATION:{escape_ical_text(location)}",
            f"DESCRIPTION:{escape_ical_text(chr(10).join(desc_lines))}",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT"
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def generate_dynamic_index(ui_data, dist_dir):
    """
    Genera una SPA HTML standalone con selettori Anno e Linea e supporto
    multi-piattaforma: Apple, Google Calendar, Microsoft Outlook, Android/Samsung e Thunderbird.
    """
    html_template = """<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calendari UniSR - Medicina e Chirurgia</title>
    <style>
        :root {
            --bg: #0f172a; --surface: #1e293b; --surface-hover: #334155;
            --text: #f8fafc; --text-muted: #94a3b8; --primary: #38bdf8;
            --border: #334155; --orange: #fb923c;
            --apple: #0284c7; --google: #1a73e8; --outlook: #0078d4;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 2rem 1rem; line-height: 1.5; }
        .container { max-width: 980px; margin: 0 auto; }
        header { text-align: center; margin-bottom: 2rem; }
        h1 { font-size: 2.1rem; margin-bottom: 0.5rem; color: #fff; }
        .subtitle { color: var(--text-muted); font-size: 1.15rem; }
        
        .selector-box {
            background: var(--surface); border: 1px solid var(--border);
            border-radius: 14px; padding: 1.5rem; margin-bottom: 2rem;
            display: flex; gap: 1rem; flex-wrap: wrap; justify-content: center; align-items: center;
        }
        select {
            padding: 0.7rem 1.2rem; border-radius: 10px; border: 1px solid #475569;
            background: #0f172a; color: #fff; font-size: 1rem; cursor: pointer;
            outline: none; min-width: 220px;
        }
        select:focus { border-color: var(--primary); }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.25rem; margin-bottom: 2.5rem; }
        .card {
            background: var(--surface); border: 1px solid var(--border);
            border-radius: 14px; padding: 1.35rem; display: flex; flex-direction: column; justify-content: space-between;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .card:hover { transform: translateY(-2px); border-color: #475569; }
        .card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; gap: 0.5rem; }
        .card-header h3 { font-size: 1.1rem; font-weight: 600; flex-grow: 1; }
        .badge { font-size: 0.75rem; font-weight: 700; padding: 0.25rem 0.6rem; border-radius: 6px; text-transform: uppercase; white-space: nowrap; }
        .card-meta { font-size: 0.85rem; color: #cbd5e1; margin-bottom: 1rem; }
        .actions { display: flex; flex-direction: column; gap: 0.5rem; }
        .actions-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
        
        .btn {
            display: flex; align-items: center; justify-content: center; gap: 0.4rem;
            text-align: center; padding: 0.6rem 0.8rem; border-radius: 8px;
            font-size: 0.82rem; font-weight: 600; text-decoration: none; cursor: pointer;
            border: none; transition: opacity 0.2s;
        }
        .btn:hover { opacity: 0.9; }
        .btn-apple { background: #0284c7; color: white; }
        .btn-gcal { background: #2563eb; color: white; }
        .btn-outlook { background: #0284c7; color: white; }
        .btn-copy { background: var(--surface-hover); color: #e2e8f0; border: 1px solid var(--border); width: 100%; }
        
        .hidden { display: none !important; }
        .section-title { font-size: 1.35rem; margin: 2.2rem 0 1rem; color: #fff; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem; }
        
        /* Guide multi-dispositivo */
        .guide-box {
            background: var(--surface); border: 1px solid var(--border);
            border-radius: 14px; padding: 1.75rem; margin-top: 3rem;
        }
        .guide-box h2 { font-size: 1.3rem; margin-bottom: 1rem; color: #fff; }
        .platforms-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.25rem; margin-top: 1rem;
        }
        .platform-card {
            background: #0f172a; border: 1px solid var(--border); border-radius: 10px; padding: 1rem;
        }
        .platform-card h4 { font-size: 0.98rem; margin-bottom: 0.4rem; color: var(--primary); display: flex; align-items: center; gap: 0.4rem; }
        .platform-card p, .platform-card li { font-size: 0.85rem; color: var(--text-muted); line-height: 1.4; }
        .platform-card ul { padding-left: 1.2rem; margin-top: 0.3rem; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Sincronizzazione Calendario UniSR</h1>
            <p class="subtitle">CdLM Medicina e Chirurgia - Tutti gli Anni e Canali</p>
        </header>

        <div class="selector-box">
            <select id="anno-select" onchange="updateLinee()">
                <option value="">-- Seleziona Anno --</option>
                <option value="1">1° Anno</option>
                <option value="2">2° Anno</option>
                <option value="3">3° Anno</option>
                <option value="4">4° Anno</option>
                <option value="5">5° Anno</option>
                <option value="6">6° Anno</option>
            </select>
            <select id="linea-select" onchange="renderFeeds()" disabled>
                <option value="">-- Prima seleziona l'Anno --</option>
            </select>
        </div>

        <div id="content-area" class="hidden">
            <!-- Box Calendario Completo Curricolare -->
            <div class="card" style="border-color: var(--primary); background: #0b1329; margin-bottom: 2rem;">
                <div class="card-header">
                    <span class="badge" style="background: #38bdf822; color: #38bdf8; border: 1px solid #38bdf8;">FEED UNICO COMPLETO</span>
                    <h3 id="full-card-title">Tutti i Corsi Curricolari Obbligatori</h3>
                </div>
                <p class="card-meta" id="ios-meta"></p>
                <div class="actions">
                    <div class="actions-row">
                        <a id="apple-full-btn" href="#" class="btn btn-apple">🍏 Apple Calendar (iOS/Mac)</a>
                        <a id="gcal-full-btn" href="#" target="_blank" class="btn btn-gcal">📅 Google Calendar</a>
                    </div>
                    <div class="actions-row">
                        <a id="outlook-full-btn" href="#" target="_blank" class="btn btn-outlook">📧 Outlook / 365</a>
                        <button id="copy-full-btn" onclick="" class="btn btn-copy">📋 Copia Link Universale (ICS)</button>
                    </div>
                </div>
            </div>

            <!-- Legenda -->
            <div class="card" style="margin-bottom: 2.5rem;">
                <h3 style="font-size: 1.15rem; margin-bottom: 0.5rem; color: #fff;">Legenda Corsi ed Eventi</h3>
                <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1rem;">
                    I corsi nel feed completo sono identificati da un codice breve per facilitarne la lettura sui dispositivi mobili:
                </p>
                <div id="legend-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.5rem; font-size: 0.85rem;">
                </div>
            </div>

            <!-- Moduli Obbligatori per Materia -->
            <h2 class="section-title">📚 Corsi per Materia (Google Calendar / Outlook / Multi-Colore)</h2>
            <p style="color:var(--text-muted); font-size:0.9rem; margin-top:-0.5rem; margin-bottom:1.25rem;">
                Sottoscrivi le singole materie per visualizzarle con colori dedicati nel tuo calendario.
            </p>
            <div class="grid" id="materie-grid"></div>

            <!-- Corsi Elettivi -->
            <h2 class="section-title">🎯 Corsi Elettivi (A scelta dello studente - Arancione)</h2>
            <p style="color:var(--text-muted); font-size:0.9rem; margin-top:-0.5rem; margin-bottom:1.25rem;">
                Sottoscrivi unicamente i corsi opzionali che hai inserito nel piano di studi.
            </p>
            <div class="grid" id="elettivi-grid"></div>
        </div>

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
                    <p>Clicca su <b>"Google Calendar"</b> per aggiungerlo direttamente con 1 clic. Da smartphone Android, assicurati che la sincronizzazione sia attiva nell'app Google Calendar.</p>
                </div>
                <div class="platform-card">
                    <h4>📧 Microsoft Outlook (Windows / Mac / Web)</h4>
                    <p>Clicca su <b>"Outlook / 365"</b> per aprire la sottoscrizione web, oppure copia il link ICS e incollalo in Outlook in <i>"Aggiungi calendario" ➔ "Iscriviti dal Web"</i>.</p>
                </div>
                <div class="platform-card">
                    <h4>📲 Samsung Calendar / Android Nativo</h4>
                    <p>Copia il link universale ICS e incollalo nell'app Calendario sotto <i>"Gestisci calendari" ➔ "Aggiungi da URL"</i>, oppure sottoscrivi tramite Google Calendar.</p>
                </div>
                <div class="platform-card">
                    <h4>📝 Notion Calendar (ex Cron)</h4>
                    <p>Aggiungi i calendari al tuo account Google Calendar: Notion Calendar li mostrerà automaticamente mantenendo colori e orari aggiornati.</p>
                </div>
                <div class="platform-card">
                    <h4>🦅 Mozilla Thunderbird & Altri</h4>
                    <p>In Thunderbird seleziona <i>Nuovo Calendario ➔ Sulla rete ➔ Formato iCalendar (ICS)</i> e incolla il link universale copiato dal pulsante.</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        const uiData = __UI_DATA_INJECT__;
        const hostPath = window.location.href.replace(/[/]index[.]html$/, '').replace(/[/]$/, '');
        
        const annoSelect = document.getElementById('anno-select');
        const lineaSelect = document.getElementById('linea-select');
        const contentArea = document.getElementById('content-area');
        const materieGrid = document.getElementById('materie-grid');
        const elettiviGrid = document.getElementById('elettivi-grid');
        
        function updateLinee() {
            const anno = parseInt(annoSelect.value);
            lineaSelect.innerHTML = '<option value="">-- Seleziona Linea --</option>';
            if (!anno) {
                lineaSelect.disabled = true;
                contentArea.classList.add('hidden');
                return;
            }
            
            lineaSelect.disabled = false;
            contentArea.classList.add('hidden');
            
            const comboDisponibili = uiData.filter(d => d.anno === anno);
            comboDisponibili.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.slug_linea;
                opt.textContent = c.linea_name.replace('PERCORSO COMUNE', '').trim() || 'Linea Comune';
                lineaSelect.appendChild(opt);
            });
        }
        
        function renderFeeds() {
            const anno = parseInt(annoSelect.value);
            const slug = lineaSelect.value;
            if (!anno || !slug) {
                contentArea.classList.add('hidden');
                return;
            }
            
            const config = uiData.find(d => d.anno === anno && d.slug_linea === slug);
            if (!config) return;
            
            // URLs per il feed completo
            const fullIcsUrl = hostPath + '/' + config.ios_link + '?v=2';
            const cleanWebcal = fullIcsUrl.replace(/^https?:[/][/]/, 'webcal://');
            const gcalFullUrl = 'https://calendar.google.com/calendar/render?cid=' + encodeURIComponent(cleanWebcal);
            const outlookFullUrl = 'https://outlook.live.com/calendar/0/addfromweb?url=' + encodeURIComponent(fullIcsUrl) + '&name=' + encodeURIComponent('UniSR ' + config.linea_name);

            document.getElementById('ios-meta').textContent = `${config.ios_count} eventi curricolari obbligatori nel semestre`;
            document.getElementById('apple-full-btn').href = cleanWebcal;
            document.getElementById('gcal-full-btn').href = gcalFullUrl;
            document.getElementById('outlook-full-btn').href = outlookFullUrl;
            document.getElementById('copy-full-btn').setAttribute('onclick', `copyFeedUrl('${config.ios_link}', this)`);
            
            // Popolamento Legenda
            const legendGrid = document.getElementById('legend-grid');
            let legendHtml = config.materie.map(m => {
                let extraDesc = (m.name.toLowerCase() === 'eventi generici') ? 
                    '<br><span style="color:var(--text-muted);font-size:0.75rem;">(Attività extra, assemblee, benvenuto matricole, ecc.)</span>' : '';
                return `<div style="background:var(--surface-hover); padding: 0.5rem; border-radius: 6px;">
                    <strong style="color:var(--primary);">[${m.abbr || '---'}]</strong> ${m.name}${extraDesc}
                </div>`;
            }).join('');
            legendGrid.innerHTML = legendHtml;
            
            function buildCard(item) {
                const itemIcsUrl = hostPath + '/' + item.file + '?v=2';
                const itemWebcal = itemIcsUrl.replace(/^https?:[/][/]/, 'webcal://');
                const gcalItemUrl = 'https://calendar.google.com/calendar/render?cid=' + encodeURIComponent(itemWebcal);
                const outlookItemUrl = 'https://outlook.live.com/calendar/0/addfromweb?url=' + encodeURIComponent(itemIcsUrl) + '&name=' + encodeURIComponent(item.name);
                
                return `
                <div class="card">
                    <div class="card-header">
                        <span class="badge" style="background: ${item.bg_hex}; color: ${item.color_hex}; border: 1px solid ${item.color_hex};">${item.color_name}</span>
                        <h3>${item.name}</h3>
                    </div>
                    <p class="card-meta"><b>${item.count}</b> sessioni in calendario</p>
                    <div class="actions">
                        <div class="actions-row">
                            <a href="${gcalItemUrl}" target="_blank" class="btn btn-gcal">📅 Google</a>
                            <a href="${itemWebcal}" class="btn btn-apple">🍏 Apple</a>
                        </div>
                        <div class="actions-row">
                            <a href="${outlookItemUrl}" target="_blank" class="btn btn-outlook">📧 Outlook</a>
                            <button onclick="copyFeedUrl('${item.file}', this)" class="btn btn-copy">📋 Copia ICS</button>
                        </div>
                    </div>
                </div>`;
            }
            
            materieGrid.innerHTML = config.materie.map(buildCard).join('');
            elettiviGrid.innerHTML = config.elettivi.map(buildCard).join('');
            if(config.elettivi.length === 0) {
                elettiviGrid.innerHTML = '<p style="color:var(--text-muted); font-size:0.95rem;">Nessun corso elettivo rilevato per questo anno/linea.</p>';
            }
            
            contentArea.classList.remove('hidden');
        }

        window.copyFeedUrl = function(filename, btn) {
            const url = hostPath + '/' + filename + '?v=2';
            navigator.clipboard.writeText(url).then(() => {
                const orig = btn.innerText;
                btn.innerText = '✅ Copiato!';
                btn.style.borderColor = '#22c55e'; btn.style.color = '#22c55e';
                setTimeout(() => { btn.innerText = orig; btn.style.borderColor = ''; btn.style.color = ''; }, 2000);
            }).catch(() => {
                prompt('Copia questo link:', url);
            });
        };
    </script>
</body>
</html>
"""
    final_html = html_template.replace('__UI_DATA_INJECT__', json.dumps(ui_data, ensure_ascii=False))
    with open(os.path.join(dist_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(final_html)
    print("Pagina web dinamica index.html generata correttamente in dist/")



def main():
    print("=== Avvio Sincronizzatore Multicanale UniSR ===")
    os.makedirs(DIST_DIR, exist_ok=True)
    load_acronyms_map()
    
    total_lezioni_estratte = 0
    total_feed_generati = 0
    ui_data = []

    for cfg in MEDICINA_CONFIG:
        if cfg['is_imd']: 
            continue
            
        print(f"\nElaborazione: Anno {cfg['anno']} - {cfg['linea_name']} ({cfg['cdl_name']})")
        html = fetch_schedule_html(cfg['cdl_id'], cfg['anno_id'], cfg['linea_id'])
        if not html:
            continue
            
        lessons = extract_lessons_from_html(html)
        print(f" -> Trovate {len(lessons)} lezioni")
        total_lezioni_estratte += len(lessons)
        
        if not lessons:
            continue
            
        group_dir = os.path.join(DIST_DIR, f"anno_{cfg['anno']}", cfg['slug_linea'])
        os.makedirs(group_dir, exist_ok=True)

        curricular = [l for l in lessons if not l['elettivo']]
        electives = [l for l in lessons if l['elettivo']]
        
        # Salvataggio iOS completo
        ios_file = "completo_ios.ics"
        ios_path = os.path.join(group_dir, ios_file)
        with open(ios_path, 'w', encoding='utf-8') as f:
            f.write(build_ics_calendar(f"UniSR Anno {cfg['anno']} - {cfg['linea_name']}", curricular, "Feed completo iOS"))
        total_feed_generati += 1
        
        # Raggruppamento per materia
        subjects = defaultdict(list)
        for l in curricular:
            base_subj = get_base_subject_name(clean_title(l['titolo']))
            subjects[base_subj].append(l)
            
        elettivi_subjects = defaultdict(list)
        for l in electives:
            base_subj = get_base_subject_name(clean_title(l['titolo']))
            elettivi_subjects[base_subj].append(l)

        combo_ui = {
            "anno": cfg['anno'],
            "linea_name": cfg['linea_name'],
            "slug_linea": cfg['slug_linea'],
            "ios_link": f"anno_{cfg['anno']}/{cfg['slug_linea']}/{ios_file}",
            "ios_count": len(curricular),
            "materie": [],
            "elettivi": []
        }

        for subj_name, subj_lessons in sorted(subjects.items()):
            slug_subj = slugify(subj_name)
            filename = f"materia_{slug_subj}.ics"
            filepath = os.path.join(group_dir, filename)
            
            color_hex, bg_hex, color_name = get_color_for_subject(subj_name)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(build_ics_calendar(f"{subj_name}", subj_lessons, f"Corso: {subj_name}"))
            total_feed_generati += 1
            
            combo_ui["materie"].append({
                "name": subj_name,
                "abbr": get_abbreviation(subj_name),
                "file": f"anno_{cfg['anno']}/{cfg['slug_linea']}/{filename}",
                "count": len(subj_lessons),
                "color_name": color_name,
                "color_hex": color_hex,
                "bg_hex": bg_hex
            })
            
        for subj_name, subj_lessons in sorted(elettivi_subjects.items()):
            slug_subj = slugify(subj_name)
            filename = f"elettivo_{slug_subj}.ics"
            filepath = os.path.join(group_dir, filename)
            
            color_hex, bg_hex, color_name = '#fb923c', '#fb923c22', 'Tangerine'
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(build_ics_calendar(f"Elettivo: {subj_name}", subj_lessons, f"Corso Elettivo: {subj_name}"))
            total_feed_generati += 1
            
            combo_ui["elettivi"].append({
                "name": subj_name,
                "abbr": get_abbreviation(subj_name),
                "file": f"anno_{cfg['anno']}/{cfg['slug_linea']}/{filename}",
                "count": len(subj_lessons),
                "color_name": color_name,
                "color_hex": color_hex,
                "bg_hex": bg_hex
            })

        ui_data.append(combo_ui)
        time.sleep(1.0)
        
    print(f"\n=== Fine ===")
    print(f"Totale Lezioni Estratte: {total_lezioni_estratte}")
    print(f"Totale Feed Generati: {total_feed_generati}")
    
    with open(os.path.join(DIST_DIR, "ui_data.json"), "w", encoding="utf-8") as f:
        json.dump(ui_data, f, ensure_ascii=False, indent=2)

    generate_dynamic_index(ui_data, DIST_DIR)


if __name__ == "__main__":
    main()
