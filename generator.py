import os
import re
from datetime import datetime
from groq import Groq
from playwright.sync_api import sync_playwright


SYSTEM_PROMPT = """Sei un editor tech senior. Ogni giorno crei una presentazione PDF sul mondo del Vibe Coding — l'approccio in cui si programma guidando un'AI invece di scrivere codice manualmente.

Il tuo lavoro è trasformare una lista di articoli grezzi in una presentazione HTML bella, utile e leggibile. Non elenchi articoli: li contestualizzi, li colleghi, dai valore editoriale.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGOLE DESIGN — NON DEVIARE MAI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ogni slide è un div con classe `slide` e DEVE avere questo wrapper esterno:
  <div class="slide bg-white" style="width:794px;min-height:1123px;padding:64px;box-sizing:border-box;page-break-after:always;display:flex;flex-direction:column;">

TIPOGRAFIA (usa SOLO queste classi):
  H1 titolo slide principale  → class="text-4xl font-black text-slate-900 leading-tight"
  H2 sezione / sottotitolo    → class="text-2xl font-bold text-slate-800 mt-2"
  H3 titolo card              → class="text-base font-semibold text-slate-800 leading-snug"
  Corpo testo                 → class="text-sm text-slate-600 leading-relaxed mt-2"
  Label / tag / fonte         → class="text-xs font-medium text-slate-400 uppercase tracking-wide mt-3"
  Accent / link visivo        → class="text-indigo-600 font-medium"

CARD:
  Singola card → <div class="bg-slate-50 rounded-2xl border border-slate-100 p-5 flex flex-col gap-2">
  Grid 2 card  → <div class="grid grid-cols-2 gap-5 mt-6">
  Grid 3 card  → <div class="grid grid-cols-3 gap-4 mt-6">

ACCENT BAR (separatore visivo sopra H1):
  <div class="w-12 h-1 bg-indigo-500 rounded-full mb-6"></div>

PILLOLA TAG:
  <span class="inline-block bg-indigo-50 text-indigo-600 text-xs font-semibold px-3 py-1 rounded-full">Testo</span>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPONENTI DISPONIBILI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. HERO — slide di apertura con data, titolo editoriale forte, frase introduttiva che inquadra la giornata

2. 2-CARD — due notizie importanti affiancate, con titolo sezione e sintesi per ciascuna

3. 3-CARD — tre notizie affiancate, utile per trend o tool del giorno

4. DEEP-DIVE — un articolo o tema approfondito: più testo, contesto, perché è rilevante oggi

5. TREND LIST — 4-6 punti chiave del giorno in forma di lista con pillole tag colorate

6. INSIGHT — slide con un'osservazione editoriale forte, un pattern che emerge, una domanda aperta al lettore

7. CLOSING — slide finale con takeaway concreti (cosa fare, cosa tenere d'occhio, cosa imparare)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LIBERTÀ EDITORIALE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Scegli TU quante slide (minimo 5, massimo 10) e di che tipo
- Se un tema domina il giorno, dagli più slide; se c'è varietà, distribuisci
- Raggruppa articoli correlati nella stessa slide se ha senso
- Scrivi in italiano, tono diretto e professionale, no gergo inutile
- Ogni card: titolo rielaborato (non copia-incolla), 3-4 righe di sintesi utile, fonte in basso
- NON inventare informazioni non presenti negli articoli
- Inserisci sempre l'URL originale dell'articolo nel tag fonte (testo visibile, non href)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Restituisci SOLO i div delle slide, senza <html>, <head>, <body>, senza markdown, senza commenti.
Usa solo classi Tailwind + gli style inline minimi già indicati nel wrapper slide.
Niente JavaScript. Niente font esterni (usiamo Inter già caricato)."""


HTML_WRAPPER = """<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <title>Vibe Coding Daily — {date}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
  <style>
    * {{ font-family: 'Inter', system-ui, sans-serif; }}
    @page {{ size: A4; margin: 0; }}
    .slide:last-child {{ page-break-after: avoid; }}
  </style>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;">
{content}
</body>
</html>"""


def generate_html(articles: list[dict]) -> str:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    articles_text = "\n\n".join(
        f"[{i+1}] {a['title']}\n"
        f"Fonte: {a['source']} | URL: {a['url']}\n"
        f"{a['snippet']}"
        for i, a in enumerate(articles)
    )

    date_str = datetime.now().strftime("%d %B %Y")
    user_message = (
        f"Data di oggi: {date_str}\n\n"
        f"Articoli raccolti ({len(articles)} totali):\n\n"
        f"{articles_text}\n\n"
        f"Crea la presentazione."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        max_tokens=6000,
        temperature=0.65,
    )

    content = response.choices[0].message.content.strip()

    # Strip markdown fences if Groq added them
    content = re.sub(r"^```[a-z]*\n?", "", content)
    content = re.sub(r"\n?```$", "", content)

    return HTML_WRAPPER.format(
        date=date_str,
        content=content.strip(),
    )


def html_to_pdf(html_content: str, output_path: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 794, "height": 1123})
        page.set_content(html_content, wait_until="networkidle", timeout=30000)
        # Extra wait for Tailwind JIT to apply classes
        page.wait_for_timeout(1500)
        page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()
