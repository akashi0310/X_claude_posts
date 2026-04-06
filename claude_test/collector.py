"""Data collection layer: twscrape (primary) + RSS fallback."""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import feedparser
from twscrape import API as TwAPI
from twscrape import gather

from config import TWITTER_ACCOUNTS

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

ACCOUNTS_DB = Path(__file__).parent / "twscrape_accounts.db"


def _post_to_dict(tweet) -> dict:
    """Convert a twscrape Tweet object to a flat dict."""
    return {
        "id": str(tweet.id),
        "username": tweet.user.username,
        "text": tweet.rawContent,
        "date": tweet.date.isoformat(),
        "likes": tweet.likeCount,
        "retweets": tweet.retweetCount,
        "replies": tweet.replyCount,
        "url": tweet.url,
        "source": "twscrape",
    }


async def scrape_with_twscrape(accounts: list[str], limit_per_account: int = 50) -> list[dict]:
    """Scrape recent posts using twscrape."""
    api = TwAPI()

    # Check if we have any logged-in accounts
    account_list = await api.pool.accounts_info()
    if not account_list:
        print("[twscrape] No accounts configured. Use `twscrape add_accounts` first.")
        print("[twscrape] Falling back to RSS...")
        return []

    posts = []
    for username in accounts:
        username = username.strip()
        try:
            print(f"[twscrape] Scraping @{username}...")
            user = await api.user_by_login(username)
            if not user:
                print(f"[twscrape] Could not find user @{username}")
                continue
            tweets = await gather(api.user_tweets(user.id, limit=limit_per_account))
            for t in tweets:
                posts.append(_post_to_dict(t))
            print(f"[twscrape] Got {len(tweets)} posts from @{username}")
        except Exception as e:
            print(f"[twscrape] Error scraping @{username}: {e}")
    return posts


def scrape_with_rss(accounts: list[str]) -> list[dict]:
    """Fallback: scrape via Nitter RSS feeds."""
    # Public Nitter instances that offer RSS
    nitter_instances = [
        "https://nitter.privacydev.net",
        "https://nitter.poast.org",
    ]

    posts = []
    for username in accounts:
        username = username.strip()
        fetched = False
        for instance in nitter_instances:
            try:
                url = f"{instance}/{username}/rss"
                print(f"[RSS] Trying {url}...")
                feed = feedparser.parse(url)
                if feed.bozo and not feed.entries:
                    continue
                for entry in feed.entries:
                    published = entry.get("published", "")
                    posts.append({
                        "id": entry.get("id", entry.get("link", "")),
                        "username": username,
                        "text": entry.get("title", "") or entry.get("summary", ""),
                        "date": published,
                        "likes": 0,
                        "retweets": 0,
                        "replies": 0,
                        "url": entry.get("link", ""),
                        "source": "rss",
                    })
                print(f"[RSS] Got {len(feed.entries)} posts from @{username}")
                fetched = True
                break
            except Exception as e:
                print(f"[RSS] Error with {instance} for @{username}: {e}")
        if not fetched:
            print(f"[RSS] Could not fetch @{username} from any instance")
    return posts


async def collect_posts(accounts: list[str] | None = None, limit: int = 50) -> list[dict]:
    """Collect posts: try twscrape first, fall back to RSS."""
    accounts = accounts or TWITTER_ACCOUNTS

    # Try twscrape first
    posts = await scrape_with_twscrape(accounts, limit_per_account=limit)

    if not posts:
        print("[collector] twscrape returned nothing, trying RSS fallback...")
        posts = scrape_with_rss(accounts)

    # Deduplicate by id
    seen = set()
    unique = []
    for p in posts:
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)

    # Save to disk
    out_path = DATA_DIR / "posts.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f"[collector] Saved {len(unique)} unique posts to {out_path}")

    return unique


if __name__ == "__main__":
    posts = asyncio.run(collect_posts())
    print(f"Collected {len(posts)} posts total.")
