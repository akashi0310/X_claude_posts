"""XCrawl API-based X/Twitter scraper. Uses AI extraction to get structured post data.

Passes X/Twitter auth cookies so XCrawl can access authenticated pages.
Cookies are extracted from the saved Playwright browser profile.
"""

import asyncio
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

PROFILE_DIR = Path(__file__).parent / "chrome_profile"
COOKIES_FILE = DATA_DIR / "x_cookies.json"

XCRAWL_API_URL = "https://run.xcrawl.com/v1/scrape"
XCRAWL_API_KEY = os.getenv("XCRAWL_API_KEY", "")


def extract_cookies_from_profile() -> dict:
    """Extract X/Twitter cookies from the saved Playwright browser profile."""
    # Try loading cached cookies first
    if COOKIES_FILE.exists():
        try:
            with open(COOKIES_FILE, "r") as f:
                cookies = json.load(f)
            if cookies.get("auth_token") and cookies.get("ct0"):
                print("[xcrawl] Using cached X cookies")
                return cookies
        except (json.JSONDecodeError, IOError):
            pass

    # Extract fresh cookies from Playwright profile
    if not PROFILE_DIR.exists():
        print("[xcrawl] No Playwright profile found. Run 'python login_once.py' first.")
        return {}

    print("[xcrawl] Extracting cookies from Playwright profile...")
    try:
        cookies = asyncio.run(_extract_cookies_async())
        if cookies.get("auth_token"):
            with open(COOKIES_FILE, "w") as f:
                json.dump(cookies, f)
            print("[xcrawl] Cookies saved for future use")
        return cookies
    except Exception as e:
        print(f"[xcrawl] Error extracting cookies: {e}")
        return {}


async def _extract_cookies_async() -> dict:
    """Launch Playwright to grab cookies from the saved profile."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="msedge",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )

        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        all_cookies = await context.cookies("https://x.com")
        await context.close()

    # Extract the key auth cookies
    cookie_map = {}
    for c in all_cookies:
        cookie_map[c["name"]] = c["value"]

    # Return the essential ones for XCrawl
    result = {}
    for key in ("auth_token", "ct0", "twid", "guest_id", "personalization_id"):
        if key in cookie_map:
            result[key] = cookie_map[key]

    if "auth_token" not in result:
        print("[xcrawl] Warning: No auth_token found — session may be expired")
        print("[xcrawl] Run 'python login_once.py' to re-login")

    return result


def scrape_user(username: str, cookies: dict) -> list[dict]:
    """Scrape a single X/Twitter user's posts via XCrawl API with auth cookies."""
    url = f"https://x.com/{username}"
    print(f"[xcrawl] Scraping @{username}...")

    payload = {
        "url": url,
        "request": {
            "cookies": cookies,
            "device": "desktop",
        },
        "js_render": {
            "enabled": True,
            "wait_until": "networkidle",
        },
        "output": {
            "formats": ["json"],
            "json": {
                "prompt": (
                    "Extract all visible tweets/posts on this page. "
                    "For each post return only: "
                    "text (full tweet text), "
                    "url (full URL to the tweet)"
                ),
            },
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

        # Debug: if no JSON, check what we got
        if not extracted:
            md = data.get("markdown", "")
            if "sign in" in md.lower() or "log in" in md.lower():
                print(f"[xcrawl] Login wall detected for @{username} — cookies may be expired")
            elif md:
                print(f"[xcrawl] Got markdown but no JSON for @{username} (first 200 chars):")
                print(f"         {md[:200]}")
            else:
                print(f"[xcrawl] Empty response for @{username}")
            credits = result.get("total_credits_used", "?")
            print(f"[xcrawl] Credits used: {credits}")
            return []

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
            post_url = item.get("url", item.get("link", f"https://x.com/{username}"))
            posts.append({
                "id": f"xc_{hash(text)}",
                "username": username,
                "text": text,
                "url": post_url,
                "source": "xcrawl",
            })

        credits = result.get("total_credits_used", "?")
        print(f"[xcrawl] Got {len(posts)} posts from @{username} (credits: {credits})")
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

    # Get auth cookies
    cookies = extract_cookies_from_profile()
    if not cookies.get("auth_token"):
        print("[xcrawl] Error: No valid X cookies. Run 'python login_once.py' first.")
        return []

    all_posts = []
    for account in accounts:
        account = account.strip()
        posts = scrape_user(account, cookies)
        all_posts.extend(posts)

    # Load existing posts and merge with new ones
    out_path = DATA_DIR / "posts.json"
    existing = []
    if out_path.exists():
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = []

    # Deduplicate: existing + new, keeping existing entries for same ID
    seen = set()
    unique = []
    for p in existing:
        pid = p.get("id", "")
        if pid and pid not in seen:
            seen.add(pid)
            unique.append(p)
    new_count = 0
    for p in all_posts:
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)
            new_count += 1

    # Save to disk
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f"\n[xcrawl] Done! {new_count} new posts, {len(unique)} total in {out_path}")

    return unique


if __name__ == "__main__":
    posts = scrape_all()
    print(f"Collected {len(posts)} posts total.")
