import time
import requests
import feedparser
from urllib.parse import quote


def _since_timestamp(days: int = 7) -> int:
    return int(time.time()) - days * 86400


# Feed RSS di fonti selezionate — blog ufficiali, changelog, ricerca
RSS_FEEDS = [
    ("Anthropic",        "https://www.anthropic.com/rss.xml"),
    ("OpenAI",           "https://openai.com/news/rss.xml"),
    ("Google DeepMind",  "https://deepmind.google/blog/rss.xml"),
    ("GitHub Blog",      "https://github.blog/feed/"),
    ("Cursor",           "https://www.cursor.com/blog/rss.xml"),
    ("Vercel",           "https://vercel.com/atom"),
    ("LangChain",        "https://blog.langchain.dev/rss/"),
    ("Hugging Face",     "https://huggingface.co/blog/feed.xml"),
    ("Simon Willison",   "https://simonwillison.net/atom/everything/"),
]

# HN: solo storie con almeno 50 punti degli ultimi 7 giorni
HN_QUERIES = [
    "AI coding tools",
    "LLM agent",
    "cursor editor",
    "claude code",
    "copilot",
]


def fetch_rss_feeds(limit_per_feed: int = 5) -> list[dict]:
    since = _since_timestamp(days=7)
    items = []
    for source_name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                if count >= limit_per_feed:
                    break
                # Filtra per data se disponibile
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    import calendar
                    ts = calendar.timegm(published)
                    if ts < since:
                        continue
                import re
                snippet = re.sub(r"<[^>]+>", "", entry.get("summary", ""))[:400]
                items.append({
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "source": source_name,
                    "snippet": snippet,
                    "points": 999,  # fonti primarie hanno priorità
                    "created_at": ts if published else 0,
                })
                count += 1
            print(f"  RSS {source_name}: {count} articoli")
        except Exception as e:
            print(f"  Warning — RSS {source_name} fallito: {e}")
    return items


def fetch_hackernews(query: str, limit: int = 10, min_points: int = 50) -> list[dict]:
    since = _since_timestamp(days=7)
    url = (
        f"https://hn.algolia.com/api/v1/search?query={quote(query)}"
        f"&tags=story&hitsPerPage={limit}"
        f"&numericFilters=created_at_i>{since},points>{min_points}"
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


def scrape_all() -> list[dict]:
    articles = []

    print("  Fetching RSS feeds...")
    articles.extend(fetch_rss_feeds())

    for query in HN_QUERIES:
        try:
            results = fetch_hackernews(query=query)
            articles.extend(results)
            print(f"  HN '{query}': {len(results)} articoli")
        except Exception as e:
            print(f"  Warning — HN '{query}' fallito: {e}")

    # Deduplicazione per URL
    seen_urls = set()
    unique = []
    for a in articles:
        if a["url"] and a["url"] not in seen_urls:
            seen_urls.add(a["url"])
            unique.append(a)

    # Fonti primarie (points=999) prima, poi per recency
    unique.sort(key=lambda x: (x["points"] == 999, x.get("created_at", 0)), reverse=True)

    print(f"  Totale articoli unici: {len(unique)}")
    return unique
