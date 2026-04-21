import requests
import feedparser
from urllib.parse import quote


def fetch_hackernews(query: str, limit: int = 15) -> list[dict]:
    url = f"https://hn.algolia.com/api/v1/search?query={quote(query)}&tags=story&hitsPerPage={limit}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    items = []
    for hit in r.json().get("hits", []):
        if hit.get("title") and hit.get("url"):
            items.append({
                "title": hit["title"],
                "url": hit["url"],
                "source": "Hacker News",
                "snippet": (hit.get("story_text") or "")[:400],
                "points": hit.get("points", 0),
            })
    return items


def fetch_devto(tag: str, limit: int = 10) -> list[dict]:
    url = f"https://dev.to/api/articles?tag={tag}&per_page={limit}&top=1"
    r = requests.get(url, timeout=10, headers={"User-Agent": "VibeNewsBotDailyV1"})
    if r.status_code != 200:
        return []
    items = []
    for art in r.json():
        items.append({
            "title": art["title"],
            "url": art["url"],
            "source": "Dev.to",
            "snippet": art.get("description") or "",
            "points": art.get("positive_reactions_count", 0),
        })
    return items


def fetch_google_news_rss(query: str, limit: int = 10) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:limit]:
        snippet = entry.get("summary", "")
        # Google News wraps in HTML, strip tags roughly
        import re
        snippet = re.sub(r"<[^>]+>", "", snippet)[:400]
        items.append({
            "title": entry.title,
            "url": entry.link,
            "source": entry.get("source", {}).get("title", "Google News"),
            "snippet": snippet,
            "points": 0,
        })
    return items


def scrape_all() -> list[dict]:
    sources = [
        (fetch_hackernews, {"query": "vibe coding"}),
        (fetch_hackernews, {"query": "AI coding tools"}),
        (fetch_devto, {"tag": "vibecoding"}),
        (fetch_devto, {"tag": "aitools"}),
        (fetch_devto, {"tag": "llm"}),
        (fetch_google_news_rss, {"query": "vibe coding"}),
        (fetch_google_news_rss, {"query": "AI pair programming 2025"}),
    ]

    articles = []
    for fn, kwargs in sources:
        try:
            results = fn(**kwargs)
            articles.extend(results)
            print(f"  {fn.__name__}({kwargs}): {len(results)} articoli")
        except Exception as e:
            print(f"  Warning — {fn.__name__}({kwargs}) fallito: {e}")

    seen_urls = set()
    unique = []
    for a in articles:
        if a["url"] not in seen_urls:
            seen_urls.add(a["url"])
            unique.append(a)

    unique.sort(key=lambda x: x["points"], reverse=True)
    return unique
