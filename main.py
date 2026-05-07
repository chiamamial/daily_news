import sys

from scraper import scrape_all
from generator import generate_html
from mailer import send_email

HTML_PATH = "/tmp/vibe_coding_daily.html"


def main() -> None:
    print("=== Vibe Coding Daily ===")

    print("\n[1/3] Scraping news...")
    articles = scrape_all()

    if not articles:
        print("Nessun articolo trovato. Uscita.")
        sys.exit(1)

    print("\n[2/3] Generazione email con Groq...")
    subject, html = generate_html(articles)
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"      HTML salvato in {HTML_PATH}")

    print("\n[3/3] Invio email...")
    send_email(subject, html)

    print("\n=== Completato ===")


if __name__ == "__main__":
    main()
