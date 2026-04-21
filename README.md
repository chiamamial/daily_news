# Vibe Coding Daily

Presentazione PDF giornaliera sul mondo del Vibe Coding, generata automaticamente via GitHub Actions.

## Come funziona

1. **Scraper** — raccoglie articoli da Hacker News, Dev.to e Google News RSS
2. **Groq AI** — legge gli articoli e crea una presentazione HTML con libertà editoriale
3. **Playwright** — converte l'HTML in PDF A4 pixel-perfect
4. **Email** — consegna il PDF via Gmail ogni mattina

## Setup

### 1. Clona il repo su GitHub

### 2. Aggiungi i secrets in `Settings → Secrets → Actions`

| Secret | Descrizione |
|---|---|
| `GROQ_API_KEY` | API key da [console.groq.com](https://console.groq.com) (gratuita) |
| `GMAIL_USER` | Il tuo indirizzo Gmail mittente |
| `GMAIL_APP_PASSWORD` | App password Gmail (non la password normale) |
| `RECIPIENT_EMAIL` | Email destinatario del PDF |

### 3. Come ottenere la Gmail App Password

1. Vai su [myaccount.google.com](https://myaccount.google.com)
2. Sicurezza → Verifica in due passaggi (deve essere attiva)
3. Sicurezza → App password → Crea nuova → nome "VibeNews"
4. Usa la password generata come `GMAIL_APP_PASSWORD`

### 4. Attiva il workflow

Il PDF parte automaticamente ogni lunedì-venerdì alle **9:00 ora italiana**.
Per un test immediato: `Actions → Vibe Coding Daily → Run workflow`.

## Run locale

```bash
pip install -r requirements.txt
playwright install chromium && playwright install-deps chromium

export GROQ_API_KEY="..."
export GMAIL_USER="..."
export GMAIL_APP_PASSWORD="..."
export RECIPIENT_EMAIL="..."

python main.py
```
