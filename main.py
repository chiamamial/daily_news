import os
import sys

from scraper import scrape_all
from generator import generate_html, html_to_pdf
from mailer import send_pdf

HTML_PATH = "/tmp/vibe_coding_daily.html"
PDF_PATH = "/tmp/vibe_coding_daily.pdf"


def main() -> None:
    print("=== Vibe Coding Daily ===")

    print("\n[1/4] Scraping news...")
    articles = scrape_all()
    print(f"      Totale articoli unici: {len(articles)}")

    if not articles:
        print("Nessun articolo trovato. Uscita.")
        sys.exit(1)

    print("\n[2/4] Generazione presentazione con Groq...")
    html = generate_html(articles)
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"      HTML salvato in {HTML_PATH}")

    print("\n[3/4] Conversione in PDF...")
    html_to_pdf(html, PDF_PATH)
    print(f"      PDF salvato in {PDF_PATH}")

    print("\n[4/4] Invio email...")
    send_pdf(PDF_PATH)

    print("\n=== Completato ===")


if __name__ == "__main__":
    main()
