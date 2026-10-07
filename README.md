# 📅 UniSR Sync - Calendario Accademico Medicina e Chirurgia

Sistema automatico in Cloud per sincronizzare in tempo reale l'orario delle lezioni da **EasyCourse UniSR** verso qualsiasi client di calendario: **Apple Calendar (iOS/macOS)**, **Google Calendar (Android/Web)** e **Microsoft Outlook (Windows/Office 365)**.

Copre l'intero **Corso di Laurea Magistrale a Ciclo Unico in Medicina e Chirurgia** (tutti gli anni dal **1° al 6°** e tutte le **linee e canali**).

---

## 🎯 Caratteristiche

1. **🌐 Portale Web Interattivo:** Pagina web unificata (`index.html`) con selettore dinamico a tendina (*Anno* e *Linea*) che mostra all'istante i feed corretti per il proprio percorso.
2. **📱 Feed Unico per Apple Calendar (iOS / iPadOS / macOS):** Sottoscrizione con un singolo clic via protocollo `webcal://` con tutti i corsi curricolari del semestre.
3. **🎨 Feed Singoli per Google Calendar (con Colori Intelligenti):** Suddivisione per singola materia con indicazione del colore nativo ottimale (assegnato deterministicamente tramite hash del nome) per una visualizzazione chiara e ordinata.
4. **🎯 Feed Dedicati per i Corsi Elettivi (Colore Tangerine / Arancione):** Ciascun corso a scelta dispone di un feed `.ics` indipendente per consentire la sottoscrizione unicamente dei corsi effettivi del proprio piano di studi.
5. **☁️ 100% Automatico e Gratuito:** Esecuzione serverless tramite **GitHub Actions** (aggiornamento due volte al giorno: alle 07:00 e alle 19:00 italiane) e hosting statico su **GitHub Pages** a costo zero e senza computer accesi.
6. **🔒 Precisione e Anti-Sovrapposizioni:** Algoritmo di parsing rigoroso che isola i contenitori giornalieri ufficiali, escludendo eventi fuori orario e sabato.

---

## 📲 Dispositivi e Piattaforme Supportate

Il sistema genera file standard **iCalendar (RFC 5545)** compatibili con l'intero panorama dei dispositivi moderni:

### 1. Apple (iPhone, iPad, Mac, Apple Watch)
* **Come sottoscrivere:** Dalla pagina web del portale, seleziona il tuo anno e la tua linea e tocca **"Sottoscrivi su Apple Calendar"**. iOS/macOS aprirà automaticamente l'app Calendario.
* **Sincronizzazione:** Se associato a iCloud, il calendario apparirà sincronizzato su tutti i dispositivi Apple della stessa persona.

### 2. Google Calendar (Android, Browser Desktop, App Mobile)
* **Come sottoscrivere:**
  1. Sul portale clicca su **"📋 Copia Link GCal"** accanto alla materia desiderata.
  2. Apri [Google Calendar Web](https://calendar.google.com) da browser (PC o modalità desktop su smartphone).
  3. Nella barra laterale a sinistra, accanto ad **Altri calendari**, clicca su **+** ➔ **Da URL**.
  4. Incolla il link e clicca **Aggiungi calendario**.
  5. Dal menu a tre puntini (⋮) del calendario aggiunto, assegna il colore consigliato indicato sul badge.
* **Android:** I calendari aggiunti su Google Calendar Web compariranno automaticamente nell'app Google Calendar su qualsiasi smartphone Android (assicurandosi che la spunta di sincronizzazione sia attiva nelle impostazioni dell'app).

### 3. Microsoft Outlook (Windows, Mac, Office 365, Outlook Web)
* Molto utilizzato su PC Windows e da chi sfrutta account universitari Microsoft:
  1. Copia il link del feed desiderato dal portale.
  2. Apri [Outlook sul Web](https://outlook.office.com/calendar) o l'app **Outlook per Windows / Mac**.
  3. Seleziona **Aggiungi calendario** ➔ **Iscriviti dal Web** (o *Da Internet*).
  4. Incolla il link e clicca su **Importa / Salva**.

### 4. Mozilla Thunderbird & Client Open Source (Linux / Windows)
* Seleziona **Nuovo Calendario** ➔ **Sulla rete** ➔ Formato **iCalendar (ICS)** ➔ Incolla l'URL del feed.

### 5. Notion Calendar (ex Cron)
* Connetti il tuo account Google Calendar a Notion Calendar: tutti i calendari sottoscritti su Google compariranno all'interno di Notion Calendar.

---

## 🚀 Setup Iniziale del Repository (Una Tantum)

### 1. Configurazione GitHub Pages
1. Nel tuo repository su GitHub, accedi a **Settings** ➔ **Pages** (menu laterale).
2. Sotto **Build and deployment** ➔ **Source**, seleziona:
   👉 **GitHub Actions** (non "Deploy from a branch").
3. Vai nella scheda **Actions** del repository: vedrai avviarsi il workflow `Sincronizza Calendari UniSR`.
4. Al termine, il tuo sito sarà attivo all'indirizzo:
   `https://<TUO-USERNAME>.github.io/<NOME-REPO>/`

## 📝 Personalizzazione Acronimi e Sigle

Gli acronimi utilizzati nei titoli degli eventi (es. `[PATO]`) e nella legenda della pagina web sono definiti nel file:
👉 **[`ACRONIMI.md`](ACRONIMI.md)**

Puoi modificare o aggiungere nuovi acronimi direttamente modificando la tabella in quel file (anche dal browser su GitHub). Alla successiva esecuzione del workflow o dello scraper, i calendari verranno generati con le sigle aggiornate.

---

## 🔔 Notifiche Push Telegram (Monitoraggio Corsi Elettivi)

Il sistema include un modulo di monitoraggio attivo per i corsi con ore parziali o in attesa di calendarizzazione (es. il corso elettivo di **Chirurgia Vascolare** con 12h previste). Quando l'università pubblica nuove date o modifiche su EasyCourse, viene inviata istantaneamente una notifica push su Telegram con l'elenco delle nuove date e il conteggio ore aggiornato.

### ⚙️ Configurazione dei Secret su GitHub (Cloud 24/7)
1. **Crea un Bot Telegram:**
   - Cerca `@BotFather` su Telegram e invia il comando `/newbot`.
   - Segui i passaggi e copia il **Bot Token** (es. `123456789:ABCdefGhI...`).
   - Avvia la chat con il tuo bot premendo **Avvia** (`/start`).
2. **Ottieni il tuo Chat ID:**
   - Cerca `@userinfobot` su Telegram e premi Avvia: ti restituirà il tuo **Id** numerico.
3. **Aggiungi i Secret su GitHub:**
   - Nel tuo repository GitHub, vai su **Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ **New repository secret**.
   - Aggiungi `TELEGRAM_BOT_TOKEN` con il token del bot.
   - Aggiungi `TELEGRAM_CHAT_ID` con il tuo ID numerico.

### 🧪 Test Locale
Puoi testare la connessione o eseguire la verifica manualmente da terminale:
```bash
# Test connessione e invio messaggio di prova
export TELEGRAM_BOT_TOKEN="il_tuo_token"
export TELEGRAM_CHAT_ID="il_tuo_chat_id"
python src/notifications.py --test-telegram

# Verifica immediata dello stato del corso su EasyCourse
python src/notifications.py --check-now
```

---

## 🛠️ Esecuzione Locale (Opzionale)

Puoi avviare lo scraper in locale in qualsiasi momento senza installare pacchetti esterni (utilizza solo moduli nativi della standard library di Python):

```bash
python src/scraper.py
```

I file generati e la pagina web saranno salvati nella cartella `dist/`.
