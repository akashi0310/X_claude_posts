"""Playwright-based X/Twitter scraper. Uses real Chrome profile to avoid detection."""

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from config import TWITTER_ACCOUNTS

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Persistent profile for Playwright (separate from your main Chrome to avoid conflicts)
PROFILE_DIR = Path(__file__).parent / "chrome_profile"


async def login_to_x(page, username: str, password: str):
    """Log into X/Twitter."""
    print("[scraper] Navigating to X login page...")
    await page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(3000)

    # Enter username/email
    print("[scraper] Entering username...")
    username_input = page.locator('input[autocomplete="username"]')
    await username_input.wait_for(timeout=15000)
    await username_input.fill(username)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(2000)

    # Check if X asks for phone/username verification (unusual activity check)
    verification_input = page.locator('input[data-testid="ocfEnterTextTextInput"]')
    if await verification_input.count() > 0:
        print("[scraper] X is asking for verification.")
        print("[scraper] Please complete it in the browser window. Waiting 60 seconds...")
        await page.wait_for_timeout(60000)

    # Enter password
    print("[scraper] Entering password...")
    password_input = page.locator('input[type="password"]')
    await password_input.wait_for(timeout=15000)
    await password_input.fill(password)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(5000)

    # Verify login success
    if "home" in page.url.lower() or "x.com" in page.url:
        print("[scraper] Login successful!")
        return True
    else:
        print(f"[scraper] Login may have failed. Current URL: {page.url}")
        return False


async def scrape_user_posts(page, username: str, max_scrolls: int = 15) -> list[dict]:
    """Navigate to a user's profile and scrape their posts."""
    url = f"https://x.com/{username}"
    print(f"\n[scraper] Visiting {url}...")
    await page.goto(url, wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(5000)

    posts = []
    seen_ids = set()
    no_new_count = 0

    for scroll in range(max_scrolls):
        # Click all "Show more" buttons to expand truncated tweets
        show_more_buttons = await page.locator('[data-testid="tweet-text-show-more-link"]').all()
        for btn in show_more_buttons:
            try:
                await btn.click()
                await page.wait_for_timeout(500)
            except Exception:
                pass

        # Extract tweet articles from the page
        articles = await page.locator('article[data-testid="tweet"]').all()

        new_count = 0
        for article in articles:
            try:
                post = await _extract_post(article, username)
                if post and post["id"] not in seen_ids:
                    seen_ids.add(post["id"])
                    posts.append(post)
                    new_count += 1
            except Exception:
                continue

        print(f"[scraper] @{username} — scroll {scroll + 1}/{max_scrolls}, "
              f"found {new_count} new ({len(posts)} total)")

        if new_count == 0:
            no_new_count += 1
            if no_new_count >= 3:
                print(f"[scraper] No new posts after 3 scrolls, stopping.")
                break
        else:
            no_new_count = 0

        # Scroll down
        await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
        await page.wait_for_timeout(2000)

    return posts


async def _extract_post(article, fallback_username: str) -> dict | None:
    """Extract post data from a tweet article element."""
    # Get tweet text
    text_el = article.locator('[data-testid="tweetText"]')
    text = ""
    if await text_el.count() > 0:
        text = await text_el.first.inner_text()

    if not text:
        return None

    # Get the post link (contains the tweet ID)
    time_el = article.locator("time")
    post_url = ""
    tweet_id = ""
    date_str = ""

    if await time_el.count() > 0:
        date_str = await time_el.first.get_attribute("datetime") or ""
        # The parent <a> of <time> has the post URL
        parent_link = time_el.first.locator("xpath=..")
        if await parent_link.count() > 0:
            href = await parent_link.get_attribute("href") or ""
            if href:
                post_url = f"https://x.com{href}"
                # Extract tweet ID from URL like /username/status/123456
                match = re.search(r"/status/(\d+)", href)
                if match:
                    tweet_id = match.group(1)

    # Get username from the post
    username = fallback_username
    user_links = article.locator('a[role="link"][href*="/"]')
    for i in range(min(await user_links.count(), 5)):
        href = await user_links.nth(i).get_attribute("href") or ""
        if href.startswith("/") and "/status/" not in href and href.count("/") == 1:
            username = href.strip("/")
            break

    # Get engagement metrics
    likes = await _get_metric(article, 'like')
    retweets = await _get_metric(article, 'retweet')
    replies = await _get_metric(article, 'reply')

    return {
        "id": tweet_id or f"pw_{hash(text)}",
        "username": username,
        "text": text,
        "date": date_str,
        "likes": likes,
        "retweets": retweets,
        "replies": replies,
        "url": post_url,
        "source": "playwright",
    }


async def _get_metric(article, metric_name: str) -> int:
    """Extract a metric (like, retweet, reply) count from a tweet."""
    btn = article.locator(f'button[data-testid="{metric_name}"]')
    if await btn.count() > 0:
        label = await btn.first.get_attribute("aria-label") or ""
        # aria-label like "123 Likes" or "5 replies"
        match = re.search(r"(\d+)", label)
        if match:
            return int(match.group(1))
    return 0


async def scrape_all(
    x_username: str = "",
    x_password: str = "",
    accounts: list[str] | None = None,
    max_scrolls: int = 15,
    headless: bool = False,
) -> list[dict]:
    """Main scraping function: uses saved session from login_once.py."""
    accounts = accounts or TWITTER_ACCOUNTS

    if not PROFILE_DIR.exists():
        print("[scraper] No saved session found!")
        print("[scraper] Run 'python login_once.py' first to log in manually.")
        return []

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="msedge",
            headless=headless,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )

        page = context.pages[0] if context.pages else await context.new_page()

        # Check if session is still valid
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(5000)

        if "login" in page.url.lower() or "flow" in page.url.lower():
            print("[scraper] Session expired! Run 'python login_once.py' again.")
            await context.close()
            return []

        print("[scraper] Logged in successfully using saved session.")

        # Scrape each account
        all_posts = []
        for account in accounts:
            account = account.strip()
            try:
                posts = await scrape_user_posts(page, account, max_scrolls=max_scrolls)
                all_posts.extend(posts)
            except Exception as e:
                print(f"[scraper] Error scraping @{account}: {e}")

        await context.close()

    # Deduplicate
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
    print(f"\n[scraper] Done! Saved {len(unique)} unique posts to {out_path}")

    return unique


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    x_user = os.getenv("X_USERNAME", "")
    x_pass = os.getenv("X_PASSWORD", "")

    if not x_user or not x_pass:
        print("Set X_USERNAME and X_PASSWORD in your .env file")
        sys.exit(1)

    posts = asyncio.run(scrape_all(x_user, x_pass))
    print(f"Collected {len(posts)} posts total.")
