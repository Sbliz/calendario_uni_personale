#!/usr/bin/env python3
"""
Modulo Notifiche Telegram per Corsi Monitorati (UniSR)
Controlla aggiornamenti orari/date (es. raggiungimento 12h per Chirurgia Vascolare)
e invia notifiche push istantanee via Bot Telegram.
"""

import os
import sys
import json
import ssl
import urllib.request
from datetime import datetime

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watched_state.json")
GIORNI_SETTIMANA = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

WATCHED_CONFIG = [
    {
        "course_id": "urgenze_chirurgia_vascolare",
        "name_keyword": "chirurgia vascolare",
        "title": "Urgenze ed emergenze in chirurgia vascolare: tempo di pace e tempo di guerra",
        "anno": 3,
        "expected_hours": 12.0
    }
]


def load_env_file():
    """Carica variabili d'ambiente da eventuale file .env nel root del progetto."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(root_dir, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            print(f"[Warning] Impossibile leggere .env: {e}")


def get_telegram_credentials():
    """Restituisce TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID."""
    load_env_file()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    return token, chat_id


def send_telegram_notification(token, chat_id, message_html):
    """Invia un messaggio formattato HTML su Telegram tramite HTTP POST nativo."""
    if not token or not chat_id:
        print("[Telegram] Avviso: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID non configurati. Notifica saltata.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }).encode("utf-8")

    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            if resp.status == 200:
                print("[Telegram] Notifica inviata con successo!")
                return True
    except Exception as e:
        print(f"[Telegram] Errore nell'invio del messaggio: {e}")
        return False


def calculate_lesson_hours(ora_inizio, ora_fine):
    """Calcola le ore della lezione da 'HH:MM' a 'HH:MM'."""
    try:
        h1, m1 = map(int, ora_inizio.split(":"))
        h2, m2 = map(int, ora_fine.split(":"))
        return round(((h2 * 60 + m2) - (h1 * 60 + m1)) / 60.0, 2)
    except Exception:
        return 0.0


def format_lesson_date(date_str):
    """Formatta '12-11-2026' con il giorno della settimana (es. 'Giovedì 12/11/2026')."""
    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y")
        giorno = GIORNI_SETTIMANA[dt.weekday()]
        return f"{giorno} {dt.strftime('%d/%m/%Y')}"
    except Exception:
        return date_str


def load_watched_state():
    """Carica lo stato salvato dei corsi monitorati."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Warning] Errore lettura {STATE_FILE}: {e}")
    return {}


def save_watched_state(state):
    """Salva lo stato aggiornato su file JSON."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Errore] Impossibile salvare {STATE_FILE}: {e}")


def check_and_notify_watched_courses(all_lessons):
    """
    Verifica se ci sono aggiornamenti rispetto allo stato salvato
    per i corsi nella configurazione WATCHED_CONFIG.
    """
    token, chat_id = get_telegram_credentials()
    state = load_watched_state()
    has_changes = False

    for cfg in WATCHED_CONFIG:
        cid = cfg["course_id"]
        keyword = cfg["name_keyword"].lower()
        title = cfg["title"]
        expected_hours = cfg["expected_hours"]

        # Filtra e deduplica le lezioni estratte per questo corso
        matching_lessons = []
        seen_keys = set()
        for l in all_lessons:
            if keyword in l.get("titolo", "").lower():
                k = (l["date"], l["ora_inizio"], l["ora_fine"], l.get("aula", ""))
                if k not in seen_keys:
                    seen_keys.add(k)
                    matching_lessons.append({
                        "date": l["date"],
                        "ora_inizio": l["ora_inizio"],
                        "ora_fine": l["ora_fine"],
                        "aula": l.get("aula", "Non specificata")
                    })

        # Ordina cronologicamente
        def sort_key(x):
            try:
                d, m, y = map(int, x["date"].split("-"))
                h, mn = map(int, x["ora_inizio"].split(":"))
                return (y, m, d, h, mn)
            except Exception:
                return (0, 0, 0, 0, 0)

        matching_lessons.sort(key=sort_key)

        # Calcola ore attuali
        current_hours = sum(calculate_lesson_hours(l["ora_inizio"], l["ora_fine"]) for l in matching_lessons)

        prev_info = state.get(cid, {})
        prev_lessons = prev_info.get("lessons", [])
        prev_hours = prev_info.get("total_hours", 0.0)

        # Confronto
        prev_keys = {(l["date"], l["ora_inizio"], l["ora_fine"], l.get("aula", "")) for l in prev_lessons}
        curr_keys = {(l["date"], l["ora_inizio"], l["ora_fine"], l.get("aula", "")) for l in matching_lessons}

        if curr_keys != prev_keys:
            has_changes = True
            new_keys = curr_keys - prev_keys
            removed_keys = prev_keys - curr_keys

            print(f"[Watch] Modifiche rilevate per '{title}':")
            print(f" -> Ore precedenti: {prev_hours}h ({len(prev_lessons)} lezioni)")
            print(f" -> Nuove ore: {current_hours}h ({len(matching_lessons)} lezioni)")

            # Costruzione messaggio Telegram
            if current_hours >= expected_hours:
                status_text = f"🎯 <b>Target {expected_hours:.0f}h raggiunto!</b>"
            else:
                mancanti = expected_hours - current_hours
                status_text = f"⏳ In attesa di ulteriori ore ({current_hours:.0f}h/{expected_hours:.0f}h, mancano {mancanti:.0f}h)"

            msg_parts = [
                "🔔 <b>UniSR — Aggiornamento Corso Elettivo!</b>\n",
                f"📚 <b>{title}</b>",
                f"📊 <b>Monte Ore:</b> {current_hours:.0f}h / {expected_hours:.0f}h previste — {status_text}\n"
            ]

            if new_keys:
                msg_parts.append("✨ <b>Nuove lezioni aggiunte:</b>")
                for l in matching_lessons:
                    k = (l["date"], l["ora_inizio"], l["ora_fine"], l.get("aula", ""))
                    if k in new_keys:
                        msg_parts.append(
                            f"  • <b>{format_lesson_date(l['date'])}</b> | "
                            f"{l['ora_inizio']}–{l['ora_fine']} | "
                            f"<i>{l['aula']}</i>"
                        )
                msg_parts.append("")

            if removed_keys:
                msg_parts.append("⚠️ <b>Lezioni rimosse o modificate:</b>")
                for l in prev_lessons:
                    k = (l["date"], l["ora_inizio"], l["ora_fine"], l.get("aula", ""))
                    if k in removed_keys:
                        msg_parts.append(
                            f"  • {format_lesson_date(l['date'])} | "
                            f"{l['ora_inizio']}–{l['ora_fine']} | "
                            f"{l['aula']}"
                        )
                msg_parts.append("")

            msg_parts.append(f"📅 <b>Calendario Completo ({len(matching_lessons)} lezioni — {current_hours:.0f} ore):</b>")
            for idx, l in enumerate(matching_lessons, 1):
                msg_parts.append(
                    f"{idx}. <b>{format_lesson_date(l['date'])}</b> | "
                    f"{l['ora_inizio']}–{l['ora_fine']} | "
                    f"<i>{l['aula']}</i>"
                )

            msg_parts.append("\n📲 <i>I calendari .ics sono stati sincronizzati automaticamente.</i>")
            full_msg = "\n".join(msg_parts)

            send_telegram_notification(token, chat_id, full_msg)

            # Aggiorna stato
            state[cid] = {
                "course_id": cid,
                "name_keyword": keyword,
                "title": title,
                "anno": cfg.get("anno", 3),
                "expected_hours": expected_hours,
                "total_hours": current_hours,
                "lessons_count": len(matching_lessons),
                "lessons": matching_lessons,
                "last_updated": datetime.now().isoformat()
            }
        else:
            print(f"[Watch] Nessuna modifica per '{title}' ({current_hours:.0f}h/{expected_hours:.0f}h, {len(matching_lessons)} lezioni).")

    if has_changes:
        save_watched_state(state)

    return has_changes


def check_watched_standalone():
    """Controlla rapidamente solo il 3° anno su EasyCourse senza fare lo scraping completo."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from scraper import fetch_schedule_html, extract_lessons_from_html

    print("Verifica rapida EasyCourse per il 3° Anno Medicina...")
    # CdL 456, Anno 1081, Linea 1730 (Verde)
    html = fetch_schedule_html(456, 1081, 1730)
    if not html:
        print("[Errore] Impossibile scaricare l'orario del 3° anno.")
        return False

    lessons = extract_lessons_from_html(html)
    print(f"Estratte {len(lessons)} lezioni totali per il 3° anno.")
    return check_and_notify_watched_courses(lessons)


def test_telegram_connection():
    """Invia un messaggio di prova per testare Token e Chat ID."""
    token, chat_id = get_telegram_credentials()
    if not token or not chat_id:
        print("[Errore] Token o Chat ID mancanti in ambiente o file .env.")
        print("Assicurati di aver impostato:")
        print("  export TELEGRAM_BOT_TOKEN='il_tuo_token'")
        print("  export TELEGRAM_CHAT_ID='il_tuo_chat_id'")
        print("oppure di aver creato un file .env nel root del progetto.")
        return False

    now_str = datetime.now().strftime("%d/%m/%Y alle %H:%M")
    test_msg = (
        "🤖 <b>Test Notifiche Telegram UniSR Riuscito!</b>\n\n"
        f"Data/Ora: {now_str}\n\n"
        "Il bot è connesso correttamente e monitora il corso elettivo:\n"
        "👉 <b>Urgenze ed emergenze in chirurgia vascolare</b> (3° anno)\n\n"
        "Riceverai un messaggio automatico non appena l'università caricherà nuove date o raggiungerà le 12 ore previste!"
    )
    return send_telegram_notification(token, chat_id, test_msg)


if __name__ == "__main__":
    if "--test-telegram" in sys.argv:
        print("Invio messaggio di test Telegram...")
        success = test_telegram_connection()
        sys.exit(0 if success else 1)
    elif "--check-now" in sys.argv:
        check_watched_standalone()
    else:
        print("Uso:")
        print("  python src/notifications.py --test-telegram   (test connessione Bot Telegram)")
        print("  python src/notifications.py --check-now        (verifica immediata del corso su EasyCourse)")
