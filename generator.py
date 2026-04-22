import json
import os
import re
from datetime import datetime
from groq import Groq
from playwright.sync_api import sync_playwright

SLIDE_W = 1280
SLIDE_H = 720

# ─── SYSTEM PROMPT ────────────────────────────────────────────────────────────
# The LLM only decides content + which layout to use.
# Python renders all HTML from templates.

SYSTEM_PROMPT = """Sei un editor tech senior di una newsletter professionale sul Vibe Coding — l'approccio in cui si programma guidando un'AI invece di scrivere codice manualmente. I tuoi lettori sono developer e tech lead che usano AI ogni giorno nel loro lavoro.

Il tuo compito è trasformare articoli grezzi in una presentazione con valore editoriale reale. Non riassumi: interpreti, colleghi, dai un punto di vista.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COME SCRIVERE — regole di stile obbligatorie
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TITOLI (headline, title nei campi JSON):
  ✗ SBAGLIATO: "OpenAI rilascia nuovo modello GPT-5"
  ✓ GIUSTO:    "GPT-5 cambia le regole: cosa significa per chi usa AI per programmare"
  ✗ SBAGLIATO: "Anthropic annuncia aggiornamenti a Claude"
  ✓ GIUSTO:    "Claude diventa più autonomo — e il confine col programmatore si fa più sottile"
  → Il titolo deve dire perché la notizia conta, non solo cosa è successo.

SINTESI (body, items):
  ✗ SBAGLIATO: "L'azienda ha annunciato un nuovo prodotto con funzionalità avanzate."
  ✓ GIUSTO:    "Cursor ha integrato la modalità agente direttamente nell'editor: ora puoi delegare task interi invece di singole modifiche. Per un developer che usa Vibe Coding, significa meno interruzioni e contesto che rimane aperto tra un'azione e l'altra."
  → Rispondi sempre a: cosa è cambiato + perché un developer che usa AI se ne deve accorgere + quale impatto concreto ha sul suo flusso di lavoro.

ANALISI (why, points, context):
  ✗ SBAGLIATO: "Questa notizia è importante per il settore tech."
  ✓ GIUSTO:    "È la prima volta che un editor mainstream tratta l'agente come unità di lavoro primaria, non come feature aggiuntiva. Segnala che il mercato si sta spostando dal 'suggerimento di codice' all''esecuzione autonoma'."
  → Esprimi un punto di vista. Individua il pattern che emerge, la tensione tra posizioni, il cambiamento che questa notizia accelera.

TAKEAWAY (closing):
  ✗ SBAGLIATO: "Tieni d'occhio i nuovi sviluppi nel settore AI."
  ✓ GIUSTO:    "Testa la modalità agente di Cursor su un task reale questa settimana — non per velocità, ma per capire dove il controllo ti manca ancora."
  → Azione specifica, non consiglio generico. Il lettore deve poterla fare domani mattina.

HEADLINE hero:
  → Una frase che cattura il tema dominante della giornata, come un titolo di copertina.
  → Deve essere incisiva, non neutra. Può essere una tensione, una domanda, un'affermazione forte.
  → Esempi: "L'AI scrive codice. Tu scrivi le regole." / "Agenti ovunque, fiducia da costruire" / "Il momento in cui il copilota diventa pilota"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROCESSO — fallo prima di costruire il JSON
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Leggi tutti gli articoli e individua: qual è il tema dominante? Ci sono filoni secondari? C'è una tensione o contraddizione tra notizie diverse?
2. Decidi il filo narrativo: la presentazione deve avere un senso dall'inizio alla fine, non essere una lista di notizie.
3. Scegli i layout in base a quanto spazio merita ogni contenuto.
4. Scrivi i testi come un editor, non come un summarizer.

Restituisci SOLO un oggetto JSON valido, senza markdown, senza commenti, senza testo prima o dopo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYOUT DISPONIBILI — scegli in base al contenuto
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"hero"
  → Prima slide. Sempre presente, sempre prima.
  → Usa per: inquadrare la giornata con un titolo editoriale forte.
  Campi: headline (titolo grande, max 8 parole), intro (2 righe che spiegano cosa succede oggi), tags (2-4 pillole tematiche)

"focus"
  → Una notizia occupa tutta la slide: sinistra sintesi, destra analisi.
  → Usa quando: una notizia è chiaramente dominante e ha molto da dire.
  Campi: label, title, body (4-5 righe di sintesi), source, why (2-3 righe "perché conta"), points (2-3 punti chiave, array di stringhe)

"two_cards"
  → Due notizie affiancate, stesso peso.
  → Usa quando: due notizie si commentano a vicenda, o hanno peso simile.
  Campi: section (titolo sezione), card1{label, title, body, source}, card2{label, title, body, source}

"three_cards"
  → Tre notizie compatte affiancate.
  → Usa quando: più notizie minori dello stesso filone, o panoramica della giornata.
  Campi: section (titolo sezione), card1{label, title, body, source}, card2{label, title, body, source}, card3{label, title, body, source}

"list_main"
  → Sinistra: lista di 4-5 segnali/punti. Destra: approfondimento su uno.
  → Usa quando: molti segnali deboli da aggregare, o lista di tool/aggiornamenti con un protagonista.
  Campi: section, items (array di stringhe, max 5), main_label, main_title, main_body, main_source

"quote"
  → Slide centrata con osservazione editoriale forte.
  → Usa quando: vuoi isolare una contraddizione, un pattern, una domanda aperta che emerge dai dati.
  Campi: label ("INSIGHT DEL GIORNO" o simile), quote (frase forte, max 25 parole), context (2 righe di spiegazione)

"closing"
  → Ultima slide. Sempre presente, sempre ultima.
  → Usa per: 3-4 takeaway concreti e azionabili.
  Campi: takeaways (array di oggetti con: color ["indigo"|"green"|"orange"|"rose"], label, body)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGOLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Minimo 5 slide, massimo 8. Prima sempre "hero", ultima sempre "closing".
- Il layout deve servire il contenuto: se una notizia è ricca, usala in "focus"; se sono 3 notizie minori, usa "three_cards".
- Titoli: rielaborati, incisivi. Non copiare dall'originale.
- Sintesi: cosa è successo + perché conta per chi usa AI per programmare + impatto concreto.
- NON inventare fatti non presenti negli articoli.
- source: solo il dominio (es. techcrunch.com).
- Labels pertinenti: "AI Tools", "Open Source", "Dev Experience", "Mercato", "Sicurezza", "Ricerca", "Framework", "LLM".
- Scrivi in italiano, tono diretto e professionale.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
  "date": "22 Aprile 2026",
  "slides": [
    {"type": "hero", "headline": "...", "intro": "...", "tags": ["...", "..."]},
    {"type": "focus", "label": "...", "title": "...", "body": "...", "source": "...", "why": "...", "points": ["...", "..."]},
    {"type": "two_cards", "section": "...", "card1": {"label":"...","title":"...","body":"...","source":"..."}, "card2": {"label":"...","title":"...","body":"...","source":"..."}},
    {"type": "three_cards", "section": "...", "card1": {...}, "card2": {...}, "card3": {...}},
    {"type": "list_main", "section": "...", "items": ["..."], "main_label": "...", "main_title": "...", "main_body": "...", "main_source": "..."},
    {"type": "quote", "label": "...", "quote": "...", "context": "..."},
    {"type": "closing", "takeaways": [{"color": "green", "label": "...", "body": "..."}, {"color": "indigo", "label": "...", "body": "..."}]}
  ]
}"""


# ─── HTML TEMPLATES ───────────────────────────────────────────────────────────

SLIDE_BASE = "width:1280px;height:720px;position:relative;overflow:hidden;box-sizing:border-box;page-break-after:always;font-family:'Inter',system-ui,sans-serif;background:#0f172a;"

ACCENT_COLORS = {
    "indigo": "#6366f1",
    "green":  "#34d399",
    "orange": "#fb923c",
    "rose":   "#f43f5e",
}
ACCENT_LIGHT = {
    "indigo": "#a5b4fc",
    "green":  "#6ee7b7",
    "orange": "#fdba74",
    "rose":   "#fda4af",
}


def _glow(color_hex: str, pos: str = "top-right") -> str:
    positions = {
        "top-right":    "top:-140px;right:-140px",
        "bottom-left":  "bottom:-100px;left:-100px",
        "center":       "top:50%;left:50%;transform:translate(-50%,-50%)",
    }
    return (
        f'<div style="position:absolute;{positions[pos]};width:600px;height:600px;'
        f'background:radial-gradient(circle,{color_hex}22 0%,transparent 65%);pointer-events:none;"></div>'
    )


def _accent_bar(color: str, vertical: bool = True) -> str:
    if vertical:
        return f'<div style="width:4px;height:28px;background:{color};border-radius:2px;flex-shrink:0;"></div>'
    return f'<div style="width:44px;height:3px;background:{color};border-radius:2px;"></div>'


def _label(text: str, color: str) -> str:
    return (
        f'<span style="color:{color};font-size:11px;font-weight:700;letter-spacing:.09em;'
        f'text-transform:uppercase;display:block;margin-bottom:14px;">{text}</span>'
    )


def _pill(text: str, color: str) -> str:
    return (
        f'<span style="color:{color};background:{color}18;border:1px solid {color}35;'
        f'font-size:12px;font-weight:600;padding:5px 14px;border-radius:99px;">{text}</span>'
    )


def _source(text: str) -> str:
    return f'<span style="color:#64748b;font-size:11px;">{text}</span>'


def render_hero(s: dict, date: str) -> str:
    tags_html = "".join(_pill(t, "#6366f1") for t in s.get("tags", []))
    return f"""
<div style="{SLIDE_BASE}">
  {_glow("#6366f1", "top-right")}
  {_glow("#6366f1", "bottom-left")}
  <div style="position:relative;z-index:1;height:100%;display:flex;flex-direction:column;justify-content:center;padding:72px 100px;">
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:28px;">
      {_accent_bar("#6366f1", vertical=False)}
      <span style="color:#6366f1;font-size:13px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;">Vibe Coding Daily · {date}</span>
    </div>
    <h1 style="color:#f1f5f9;font-size:66px;font-weight:900;line-height:1.08;margin:0 0 28px;max-width:900px;">{s["headline"]}</h1>
    <p style="color:#94a3b8;font-size:20px;line-height:1.65;max-width:720px;margin:0 0 44px;">{s["intro"]}</p>
    <div style="display:flex;gap:10px;flex-wrap:wrap;">{tags_html}</div>
  </div>
</div>"""


def render_focus(s: dict) -> str:
    color = "#6366f1"
    points_html = "".join(
        f'<li style="color:#94a3b8;font-size:14px;line-height:1.7;margin-bottom:6px;">{p}</li>'
        for p in s.get("points", [])
    )
    return f"""
<div style="{SLIDE_BASE}">
  <div style="height:100%;display:grid;grid-template-columns:3fr 2fr;">
    <!-- sinistra: sintesi -->
    <div style="background:#1e293b;padding:64px 56px;display:flex;flex-direction:column;justify-content:center;border-right:1px solid #334155;">
      {_label(s.get("label",""), color)}
      <h2 style="color:#f1f5f9;font-size:34px;font-weight:800;line-height:1.2;margin:0 0 20px;">{s["title"]}</h2>
      {_accent_bar(color, vertical=False)}
      <p style="color:#94a3b8;font-size:15px;line-height:1.72;margin:20px 0 0;flex:1;">{s["body"]}</p>
      <div style="margin-top:auto;padding-top:32px;">{_source(s.get("source",""))}</div>
    </div>
    <!-- destra: analisi -->
    <div style="padding:64px 48px;display:flex;flex-direction:column;justify-content:center;">
      <p style="color:#a5b4fc;font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin:0 0 16px;">Perché conta</p>
      <p style="color:#cbd5e1;font-size:15px;line-height:1.72;margin:0 0 36px;">{s.get("why","")}</p>
      <p style="color:#a5b4fc;font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin:0 0 14px;">Da tenere d'occhio</p>
      <ul style="padding-left:18px;margin:0;">{points_html}</ul>
    </div>
  </div>
</div>"""


def _card(data: dict, color: str, compact: bool = False) -> str:
    pad = "24px" if compact else "32px"
    title_size = "17px" if compact else "21px"
    body_size = "13px" if compact else "14px"
    return f"""
<div style="background:#1e293b;border-radius:16px;padding:{pad};display:flex;flex-direction:column;border:1px solid #334155;min-width:0;">
  {_label(data.get("label",""), color)}
  <h3 style="color:#f1f5f9;font-size:{title_size};font-weight:700;line-height:1.3;margin:0 0 14px;">{data["title"]}</h3>
  <p style="color:#94a3b8;font-size:{body_size};line-height:1.65;margin:0;flex:1;">{data["body"]}</p>
  <div style="margin-top:20px;">{_source(data.get("source",""))}</div>
</div>"""


def render_two_cards(s: dict) -> str:
    c1 = _card(s["card1"], "#6366f1")
    c2 = _card(s["card2"], "#34d399")
    return f"""
<div style="{SLIDE_BASE}">
  <div style="height:100%;display:flex;flex-direction:column;padding:56px 72px;">
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:36px;">
      {_accent_bar("#6366f1")}
      <h2 style="color:#f1f5f9;font-size:22px;font-weight:700;margin:0;">{s.get("section","")}</h2>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;flex:1;">{c1}{c2}</div>
  </div>
</div>"""


def render_three_cards(s: dict) -> str:
    c1 = _card(s["card1"], "#6366f1", compact=True)
    c2 = _card(s["card2"], "#fb923c", compact=True)
    c3 = _card(s["card3"], "#34d399", compact=True)
    return f"""
<div style="{SLIDE_BASE}">
  <div style="height:100%;display:flex;flex-direction:column;padding:56px 72px;">
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:36px;">
      {_accent_bar("#fb923c")}
      <h2 style="color:#f1f5f9;font-size:22px;font-weight:700;margin:0;">{s.get("section","")}</h2>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;flex:1;">{c1}{c2}{c3}</div>
  </div>
</div>"""


def render_list_main(s: dict) -> str:
    items_html = "".join(
        f'<li style="color:#cbd5e1;font-size:15px;line-height:1.7;margin-bottom:10px;padding-left:4px;">{item}</li>'
        for item in s.get("items", [])
    )
    return f"""
<div style="{SLIDE_BASE}">
  <div style="height:100%;display:grid;grid-template-columns:2fr 3fr;">
    <!-- sinistra: lista -->
    <div style="background:#1e293b;padding:64px 48px;display:flex;flex-direction:column;border-right:1px solid #334155;">
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:32px;">
        {_accent_bar("#fb923c")}
        <h2 style="color:#f1f5f9;font-size:20px;font-weight:700;margin:0;">{s.get("section","")}</h2>
      </div>
      <ul style="padding-left:20px;margin:0;flex:1;">{items_html}</ul>
    </div>
    <!-- destra: protagonista -->
    <div style="padding:64px 56px;display:flex;flex-direction:column;justify-content:center;">
      {_label(s.get("main_label",""), "#6366f1")}
      <h3 style="color:#f1f5f9;font-size:28px;font-weight:800;line-height:1.25;margin:0 0 20px;">{s.get("main_title","")}</h3>
      {_accent_bar("#6366f1", vertical=False)}
      <p style="color:#94a3b8;font-size:15px;line-height:1.72;margin:20px 0 0;">{s.get("main_body","")}</p>
      <div style="margin-top:auto;padding-top:32px;">{_source(s.get("main_source",""))}</div>
    </div>
  </div>
</div>"""


def render_quote(s: dict) -> str:
    return f"""
<div style="{SLIDE_BASE}">
  {_glow("#6366f1", "center")}
  <div style="position:relative;z-index:1;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:80px 120px;text-align:center;">
    <span style="color:#6366f1;font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin-bottom:36px;display:block;">{s.get("label","INSIGHT DEL GIORNO")}</span>
    <blockquote style="color:#f1f5f9;font-size:34px;font-weight:700;line-height:1.4;margin:0 0 44px;font-style:italic;">"{s["quote"]}"</blockquote>
    <p style="color:#64748b;font-size:16px;line-height:1.65;max-width:660px;margin:0;">{s.get("context","")}</p>
  </div>
</div>"""


def render_closing(s: dict) -> str:
    takeaways = s.get("takeaways", [])
    cols = min(len(takeaways), 2)
    grid = f"grid-template-columns:{'1fr ' * cols}".strip()
    cards_html = ""
    for t in takeaways:
        c = ACCENT_COLORS.get(t.get("color", "indigo"), "#6366f1")
        cl = ACCENT_LIGHT.get(t.get("color", "indigo"), "#a5b4fc")
        cards_html += (
            f'<div style="background:#1e293b;border-radius:14px;padding:28px;'
            f'border:1px solid #334155;border-left:3px solid {c};">'
            f'<p style="color:{cl};font-size:11px;font-weight:700;letter-spacing:.09em;'
            f'text-transform:uppercase;margin:0 0 12px;">{t.get("label","")}</p>'
            f'<p style="color:#cbd5e1;font-size:14px;line-height:1.65;margin:0;">{t.get("body","")}</p>'
            f'</div>'
        )
    return f"""
<div style="{SLIDE_BASE}">
  {_glow("#34d399", "bottom-left")}
  <div style="position:relative;z-index:1;height:100%;display:flex;flex-direction:column;justify-content:center;padding:60px 80px;">
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:40px;">
      {_accent_bar("#34d399")}
      <h2 style="color:#f1f5f9;font-size:22px;font-weight:700;margin:0;">TAKEAWAY DI OGGI</h2>
    </div>
    <div style="display:grid;{grid};gap:20px;">{cards_html}</div>
  </div>
</div>"""


RENDERERS = {
    "hero":        render_hero,
    "focus":       render_focus,
    "two_cards":   render_two_cards,
    "three_cards": render_three_cards,
    "list_main":   render_list_main,
    "quote":       render_quote,
    "closing":     render_closing,
}


# ─── HTML WRAPPER ─────────────────────────────────────────────────────────────

HTML_WRAPPER = """<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <title>Vibe Coding Daily — {date}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,700&display=swap" rel="stylesheet">
  <style>
    * {{ margin:0;padding:0;box-sizing:border-box; }}
    body {{ background:#000; }}
    @page {{ size:{w}px {h}px; margin:0; }}
    div[style*="page-break-after"]:last-child {{ page-break-after:avoid!important; }}
  </style>
</head>
<body>
{content}
</body>
</html>"""


# ─── MAIN FUNCTIONS ───────────────────────────────────────────────────────────

def generate_html(articles: list[dict]) -> str:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    capped = articles[:10]
    articles_text = "\n\n".join(
        f"[{i+1}] {a['title']}\n"
        f"Fonte: {a['source']} | URL: {a['url']}\n"
        f"{a['snippet'][:220]}"
        for i, a in enumerate(capped)
    )

    date_str = datetime.now().strftime("%d %B %Y")
    user_message = (
        f"Data di oggi: {date_str}\n\n"
        f"Articoli ({len(capped)}):\n\n{articles_text}\n\n"
        f"Analizza il contenuto, decidi il filo narrativo e restituisci il JSON della presentazione."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        max_tokens=4000,
        temperature=0.5,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    data = json.loads(raw)
    date_label = data.get("date", date_str)

    slides_html = []
    for slide in data.get("slides", []):
        stype = slide.get("type")
        renderer = RENDERERS.get(stype)
        if renderer is None:
            continue
        if stype == "hero":
            html = renderer(slide, date_label)
        else:
            html = renderer(slide)
        slides_html.append(html)

    return HTML_WRAPPER.format(
        date=date_label,
        w=SLIDE_W,
        h=SLIDE_H,
        content="\n".join(slides_html),
    )


def html_to_pdf(html_content: str, output_path: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H})
        page.set_content(html_content, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        page.pdf(
            path=output_path,
            width=f"{SLIDE_W}px",
            height=f"{SLIDE_H}px",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()
