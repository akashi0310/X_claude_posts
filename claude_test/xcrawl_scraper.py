"""XCrawl API-based X/Twitter scraper. Uses AI extraction to get structured post data."""

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from config import TWITTER_ACCOUNTS

load_dotenv()

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

XCRAWL_API_URL = "https://run.xcrawl.com/v1/scrape"
XCRAWL_API_KEY = os.getenv("XCRAWL_API_KEY", "")


def scrape_user(username: str) -> list[dict]:
    """Scrape a single X/Twitter user's posts via XCrawl API."""
    url = f"https://x.com/{username}"
    print(f"[xcrawl] Scraping @{username}...")

    payload = {
        "url": url,
        "output": {
            "formats": ["json"],
            "json": {
                "prompt": (
                    "Extract all visible tweets/posts on this page. "
                    "For each post return: "
                    "id (tweet ID from the URL), "
                    "username (who posted), "
                    "text (full tweet text), "
                    "date (posted date/time in ISO format), "
                    "likes (number), "
                    "retweets (number), "
                    "replies (number), "
                    "url (full URL to the tweet)"
                ),
            },
        },
        "driver": {
            "render_js": True,
            "wait": 5000,
        },
    }

    headers = {
        "Authorization": f"Bearer {XCRAWL_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(XCRAWL_API_URL, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        result = resp.json()

        # Extract posts from the AI-extracted JSON
        data = result.get("data", {})
        extracted = data.get("json", [])

        # Handle if extracted is a dict with a list inside
        if isinstance(extracted, dict):
            for key in ("posts", "tweets", "results", "data", "items"):
                if key in extracted and isinstance(extracted[key], list):
                    extracted = extracted[key]
                    break
            else:
                extracted = [extracted]

        posts = []
        for item in extracted:
            if not isinstance(item, dict):
                continue
            text = item.get("text", item.get("content", item.get("tweet", "")))
            if not text:
                continue
            posts.append({
                "id": str(item.get("id", item.get("tweet_id", f"xc_{hash(text)}"))),
                "username": item.get("username", item.get("user", username)),
                "text": text,
                "date": item.get("date", item.get("time", item.get("created_at", ""))),
                "likes": int(item.get("likes", item.get("like_count", 0)) or 0),
                "retweets": int(item.get("retweets", item.get("retweet_count", 0)) or 0),
                "replies": int(item.get("replies", item.get("reply_count", 0)) or 0),
                "url": item.get("url", item.get("link", f"https://x.com/{username}")),
                "source": "xcrawl",
            })

        credits = result.get("total_credits_used", "?")
        print(f"[xcrawl] Got {len(posts)} posts from @{username} (credits used: {credits})")
        return posts

    except requests.exceptions.HTTPError as e:
        print(f"[xcrawl] HTTP error for @{username}: {e}")
        print(f"[xcrawl] Response: {e.response.text[:500]}")
        return []
    except Exception as e:
        print(f"[xcrawl] Error scraping @{username}: {e}")
        return []


def scrape_all(accounts: list[str] | None = None) -> list[dict]:
    """Scrape all tracked accounts."""
    accounts = accounts or TWITTER_ACCOUNTS

    if not XCRAWL_API_KEY:
        print("[xcrawl] Error: Set XCRAWL_API_KEY in your .env file")
        return []

    all_posts = []
    for account in accounts:
        account = account.strip()
        posts = scrape_user(account)
        all_posts.extend(posts)

    # Deduplicate by id
    seen = set()
    unique = []
    for p in all_posts:
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)

    # Save to disk
    out_path = DATA_DIR / "posts.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f"\n[xcrawl] Done! Saved {len(unique)} unique posts to {out_path}")

    return unique


if __name__ == "__main__":
    posts = scrape_all()
    print(f"Collected {len(posts)} posts total.")
