import json
import os
import re
from datetime import datetime
from groq import Groq

SYSTEM_PROMPT = """Sei un editor tech senior di una newsletter settimanale sul mondo degli strumenti AI per sviluppatori — Cursor, Claude Code, Copilot, agenti LLM, nuovi modelli, framework, cambiamenti nel modo di lavorare dei developer.

I tuoi lettori sono developer e tech lead che usano AI ogni giorno. Non hanno tempo da perdere: vogliono sapere cosa è cambiato questa settimana e perché gli importa.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANGOLO EDITORIALE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ogni edizione risponde a una domanda implicita: "Cosa è cambiato nel mio flusso di lavoro questa settimana?"

- Se esce un nuovo modello: cosa cambia praticamente per chi lo usa per programmare?
- Se esce una feature in un editor: è un miglioramento reale o marketing?
- Se c'è un paper: ha implicazioni concrete o è accademia?
- Se c'è un pattern emergente tra più notizie: segnalalo come il vero tema della settimana.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COME SCRIVERE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TITOLI: devono dire perché conta, non cosa è successo.
  ✗ "Anthropic rilascia Claude 3.7"
  ✓ "Claude 3.7 ragiona più a lungo: cosa guadagna chi lo usa per debug"

SINTESI: cosa è cambiato + perché un developer se ne deve accorgere + impatto concreto sul flusso.
  ✗ "L'azienda ha annunciato nuove funzionalità."
  ✓ "Cursor ora può aprire più file contemporaneamente nel contesto agente. In pratica: refactoring cross-file senza dover copiare manualmente i pezzi."

ANALISI (campo why/context): esprimi un punto di vista. Individua pattern, tensioni, direzione del mercato.
  ✗ "Questa notizia è importante per il settore."
  ✓ "È il terzo editor in due mesi ad aggiungere modalità agente. Il mercato sta convergendo su un'idea: il developer non scrive righe, dirige task."

TAKEAWAY: azione specifica, non consiglio generico.
  ✗ "Tieni d'occhio i nuovi sviluppi."
  ✓ "Apri un branch di test e usa la modalità agente di Cursor su un task reale — nota dove ti manca controllo."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRUTTURA EMAIL — sezioni fisse
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Restituisci SOLO un oggetto JSON valido, senza markdown, senza testo prima o dopo.

{
  "date": "7 Maggio 2026",
  "subject": "oggetto email incisivo (max 60 caratteri)",
  "headline": "frase che cattura il tema dominante della settimana (max 10 parole)",
  "intro": "2-3 righe che inquadrano la settimana e perché è rilevante",
  "stories": [
    {
      "label": "AI Tools | LLM | Dev Experience | Open Source | Ricerca | Mercato",
      "title": "titolo rielaborato, incisivo",
      "body": "3-5 righe: cosa è successo + perché conta + impatto concreto",
      "why": "1-2 righe di punto di vista editoriale",
      "source": "nome fonte",
      "url": "url originale"
    }
  ],
  "pattern": {
    "title": "il tema trasversale della settimana (frase breve)",
    "body": "2-3 righe che collegano le notizie in un pattern più ampio"
  },
  "takeaways": [
    {"label": "cosa fare", "body": "azione specifica e concreta"}
  ]
}

REGOLE:
- stories: minimo 3, massimo 6. Solo le più rilevanti — taglia il rumore.
- takeaways: 2-3, specifici e azionabili.
- NON inventare fatti non presenti negli articoli.
- Scrivi in italiano, tono diretto e professionale.
- source: solo il nome della fonte (es. "Anthropic", "GitHub Blog").
"""


EMAIL_TEMPLATE = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;">
<tr><td align="center" style="padding:32px 16px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

  <!-- Header -->
  <tr><td style="background:#0f172a;border-radius:12px 12px 0 0;padding:36px 40px;">
    <p style="color:#6366f1;font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin:0 0 16px;">Vibe Coding Daily · {date}</p>
    <h1 style="color:#f1f5f9;font-size:28px;font-weight:800;line-height:1.25;margin:0 0 16px;">{headline}</h1>
    <p style="color:#94a3b8;font-size:15px;line-height:1.65;margin:0;">{intro}</p>
  </td></tr>

  <!-- Stories -->
  {stories_html}

  <!-- Pattern della settimana -->
  <tr><td style="background:#1e1b4b;padding:28px 40px;margin-top:4px;">
    <p style="color:#a5b4fc;font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin:0 0 10px;">PATTERN DELLA SETTIMANA</p>
    <p style="color:#f1f5f9;font-size:17px;font-weight:700;margin:0 0 10px;">{pattern_title}</p>
    <p style="color:#c7d2fe;font-size:14px;line-height:1.65;margin:0;">{pattern_body}</p>
  </td></tr>

  <!-- Takeaways -->
  <tr><td style="background:#0f172a;padding:28px 40px;">
    <p style="color:#34d399;font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin:0 0 16px;">COSA FARE QUESTA SETTIMANA</p>
    {takeaways_html}
  </td></tr>

  <!-- Footer -->
  <tr><td style="background:#0f172a;border-radius:0 0 12px 12px;padding:20px 40px;border-top:1px solid #1e293b;">
    <p style="color:#475569;font-size:12px;margin:0;">Vibe Coding Daily — generato automaticamente da fonti selezionate.</p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

STORY_TEMPLATE = """
  <tr><td style="background:#ffffff;padding:28px 40px;border-bottom:1px solid #e2e8f0;">
    <p style="color:{label_color};font-size:11px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;margin:0 0 8px;">{label}</p>
    <h2 style="color:#0f172a;font-size:18px;font-weight:700;line-height:1.3;margin:0 0 12px;">{title}</h2>
    <p style="color:#475569;font-size:14px;line-height:1.65;margin:0 0 12px;">{body}</p>
    <p style="color:#6366f1;font-size:13px;font-style:italic;margin:0 0 12px;">{why}</p>
    <a href="{url}" style="color:#94a3b8;font-size:12px;text-decoration:none;">→ {source}</a>
  </td></tr>"""

LABEL_COLORS = {
    "AI Tools":       "#6366f1",
    "LLM":            "#8b5cf6",
    "Dev Experience": "#0ea5e9",
    "Open Source":    "#10b981",
    "Ricerca":        "#f59e0b",
    "Mercato":        "#ef4444",
}


def generate_html(articles: list[dict]) -> tuple[str, str]:
    """Returns (subject, html)."""
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    capped = articles[:25]
    articles_text = "\n\n".join(
        f"[{i+1}] {a['title']}\nFonte: {a['source']} | URL: {a['url']}\n{a['snippet'][:300]}"
        for i, a in enumerate(capped)
    )

    date_str = datetime.now().strftime("%d %B %Y")
    user_message = (
        f"Data di oggi: {date_str}\n\n"
        f"Articoli disponibili ({len(capped)}):\n\n{articles_text}\n\n"
        f"Seleziona le notizie più rilevanti per un developer che usa AI, costruisci il filo narrativo e restituisci il JSON."
    )

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        max_tokens=4000,
        temperature=0.4,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    data = json.loads(raw)

    # Build stories HTML
    stories_html = ""
    for s in data.get("stories", []):
        label = s.get("label", "AI Tools")
        color = LABEL_COLORS.get(label, "#6366f1")
        stories_html += STORY_TEMPLATE.format(
            label_color=color,
            label=label,
            title=s.get("title", ""),
            body=s.get("body", ""),
            why=s.get("why", ""),
            url=s.get("url", "#"),
            source=s.get("source", ""),
        )

    # Build takeaways HTML
    takeaways_html = ""
    for t in data.get("takeaways", []):
        takeaways_html += (
            f'<p style="color:#f1f5f9;font-size:14px;line-height:1.65;margin:0 0 12px;padding-left:14px;border-left:3px solid #34d399;">'
            f'<strong style="color:#34d399;">{t.get("label","")}</strong> — {t.get("body","")}</p>'
        )

    pattern = data.get("pattern", {})
    html = EMAIL_TEMPLATE.format(
        subject=data.get("subject", f"Vibe Coding Daily — {date_str}"),
        date=data.get("date", date_str),
        headline=data.get("headline", ""),
        intro=data.get("intro", ""),
        stories_html=stories_html,
        pattern_title=pattern.get("title", ""),
        pattern_body=pattern.get("body", ""),
        takeaways_html=takeaways_html,
    )

    return data.get("subject", f"Vibe Coding Daily — {date_str}"), html
