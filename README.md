# 📅 UniSR Sync - Calendario Accademico Medicina 3

Sistema automatico in Cloud per sincronizzare in tempo reale l'orario delle lezioni da **EasyCourse UniSR** (Medicina e Chirurgia 3, canale [CLMMC-C] Linea Viola) verso **Apple Calendar (iOS)** e **Google Calendar**.

---

## 🎯 Caratteristiche

1. **📱 Feed Unico per iOS:** Un solo link `.ics` per Apple Calendar con tutte le lezioni obbligatorie del semestre.
2. **🎨 4 Feed Tematici per Google Calendar:** Suddivisi per materia per assegnare i colori nativi desiderati:
   * **Patologia** ➔ Colore: **Banana** (Giallo)
   * **Medicina di Laboratorio** (inclusi tirocini pratici) ➔ Colore: **Amethyst** (Viola)
   * **Preparedness in Medicina** ➔ Colore: **Cherry Blossom** (Rosa)
   * **Microbiologia e Microbiologia Clinica** ➔ Colore: **Eucalyptus** (Verde)
3. **🚫 Esclusione Corsi Elettivi:** I corsi elettivi opzionali sono isolati in un file a parte (`medicina3_corsi_elettivi.ics`), evitando di intasare i calendari principali prima della scelta definitiva.
4. **☁️ 100% Automatico e Gratuito:** Funziona via GitHub Actions (aggiornamento 2 volte al giorno, alle 07:00 e alle 19:00 italiane) e pubblica i file su GitHub Pages a costo zero e senza computer accesi.
5. **🌐 Portale di Sottoscrizione:** Genera una comoda pagina web (`index.html`) accessibile da smartphone con pulsante one-click *"Sottoscrivi su iOS"* e pulsanti *"Copia Link"* per Google Calendar.

---

## 🚀 Setup Iniziale (Una Tantum)

### 1. Carica il progetto su un Repository GitHub
Se non l'hai già fatto, crea un repository su [GitHub](https://github.com/new) (es. `calendario-unisr`):

```bash
git init
git add .
git commit -m "Initial commit - UniSR Calendar Sync"
git branch -M main
git remote add origin https://github.com/<TUO-USERNAME>/<NOME-REPO>.git
git push -u origin main
```

### 2. Abilita GitHub Pages per l'hosting dei calendari
1. Nel tuo repository su GitHub, vai su **Settings** > **Pages** (nel menu laterale).
2. Sotto la voce **Build and deployment** > **Source**, seleziona:
   👉 **GitHub Actions** (non "Deploy from a branch").
3. Vai nella scheda **Actions** in alto: vedrai partire il workflow `Sincronizza Calendari UniSR`.
4. Al termine dell'esecuzione (circa 20-30 secondi), GitHub Pages ti mostrerà il link del tuo sito:
   `https://<TUO-USERNAME>.github.io/<NOME-REPO>/`

---

## 📲 Come Aggiungere i Calendari

Apri da smartphone o computer il link del tuo sito GitHub Pages `https://<TUO-USERNAME>.github.io/<NOME-REPO>/`. Da lì potrai cliccare direttamente sui pulsanti oppure seguire le istruzioni manuali:

### A. Su iPhone / iPad (iOS) - Feed Unico
1. Sul portale web clicca su **"Sottoscrivi su iOS"** nel box *Calendario Unico Completo*.
2. In alternativa, su iPhone vai in:
   * **Impostazioni** > **App** > **Calendario** > **Account** > **Aggiungi account** > **Altro** > **Aggiungi calendario con sottoscrizione**.
   * Incolla il link:
     `https://<TUO-USERNAME>.github.io/<NOME-REPO>/medicina3_ios.ics`
   * Premi **Salva**. Il calendario si aggiornerà automaticamente in background.

---

### B. Su Google Calendar - 4 Feed con Colori
1. Apri [Google Calendar Web](https://calendar.google.com) da browser sul computer.
2. Nella colonna di sinistra, accanto ad **Altri calendari**, clicca sul pulsante **+** e seleziona **Da URL**.
3. Incolla il link del primo feed (es. Patologia) e clicca **Aggiungi calendario**:
   * `https://<TUO-USERNAME>.github.io/<NOME-REPO>/medicina3_patologia.ics`
4. Ripeti l'operazione per gli altri 3 feed:
   * `https://<TUO-USERNAME>.github.io/<NOME-REPO>/medicina3_med_laboratorio.ics`
   * `https://<TUO-USERNAME>.github.io/<NOME-REPO>/medicina3_preparedness.ics`
   * `https://<TUO-USERNAME>.github.io/<NOME-REPO>/medicina3_microbiologia.ics`
5. **Imposta i Colori:**
   * Trova ciascun calendario nella lista *Altri calendari*.
   * Clicca sui **tre puntini verticali (⋮)** accanto al nome:
     * Per Patologia seleziona **Banana** 🍌
     * Per Medicina di Laboratorio seleziona **Amethyst** 🟣
     * Per Preparedness seleziona **Cherry Blossom** 🌸
     * Per Microbiologia seleziona **Eucalyptus** 🍃

---

## 🛠️ Esecuzione Locale (Opzionale)

Puoi eseguire lo script anche in locale senza dipendenze esterne:

```bash
python scraper.py
```

I file generati saranno disponibili nella cartella `dist/`.
