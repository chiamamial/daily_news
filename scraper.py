import time
import requests
import feedparser
from urllib.parse import quote


def _since_timestamp(days: int = 3) -> int:
    return int(time.time()) - days * 86400


def fetch_hackernews(query: str, limit: int = 15) -> list[dict]:
    since = _since_timestamp(days=3)
    url = (
        f"https://hn.algolia.com/api/v1/search?query={quote(query)}"
        f"&tags=story&hitsPerPage={limit}"
        f"&numericFilters=created_at_i>{since}"
    )
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
                "created_at": hit.get("created_at_i", 0),
            })
    return items


def fetch_devto(tag: str, limit: int = 10) -> list[dict]:
    # Non usare top=N: restituisce articoli popolari di tutti i tempi.
    # state=fresh + sort per published_at porta articoli recenti.
    url = f"https://dev.to/api/articles?tag={tag}&per_page={limit}&state=fresh"
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
            "created_at": 0,
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

    # Prende i 5 più popolari + i rimanenti ordinati per recency, poi mescola.
    # Evita che gli stessi articoli virali di tutti i tempi occupino sempre i top 10.
    by_points = sorted(unique, key=lambda x: x["points"], reverse=True)
    top_popular = by_points[:5]
    rest_recent = [a for a in unique if a not in top_popular]
    rest_recent.sort(key=lambda x: x.get("created_at", 0), reverse=True)

    merged = top_popular + rest_recent
    # Deduplica di sicurezza dopo il merge
    seen = set()
    final = []
    for a in merged:
        if a["url"] not in seen:
            seen.add(a["url"])
            final.append(a)
    return final
