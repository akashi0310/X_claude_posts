"""Scheduler: auto scrape+index posts every N minutes. Uses XCrawl API by default."""

import asyncio
import os
import signal
import sys
import time

from dotenv import load_dotenv

load_dotenv()

DEFAULT_INTERVAL_MIN = 30


def run_xcrawl_cycle():
    """Run one scrape + index cycle using XCrawl API."""
    from xcrawl_scraper import scrape_all
    from database import index_posts

    print(f"\n[scheduler] Starting XCrawl cycle at {time.strftime('%H:%M:%S')}")
    try:
        posts = scrape_all()
        if posts:
            index_posts(posts)
        else:
            print("[scheduler] No posts collected.")
    except Exception as e:
        print(f"[scheduler] Error in cycle: {e}")


async def run_pw_cycle():
    """Run one scrape + index cycle using Playwright."""
    from pw_scraper import scrape_all
    from database import index_posts

    x_user = os.getenv("X_USERNAME", "")
    x_pass = os.getenv("X_PASSWORD", "")

    if not x_user or not x_pass:
        print("[scheduler] Error: Set X_USERNAME and X_PASSWORD in .env")
        return

    print(f"\n[scheduler] Starting Playwright cycle at {time.strftime('%H:%M:%S')}")
    try:
        posts = await scrape_all(x_user, x_pass, headless=True)
        if posts:
            index_posts(posts)
        else:
            print("[scheduler] No new posts collected.")
    except Exception as e:
        print(f"[scheduler] Error in cycle: {e}")


def run_scheduler(interval_min: int = DEFAULT_INTERVAL_MIN, use_pw: bool = False):
    """Run the scrape → index cycle on a loop."""
    mode = "Playwright" if use_pw else "XCrawl API"
    print(f"[scheduler] Auto-update every {interval_min} minutes using {mode}. Press Ctrl+C to stop.")

    if use_pw:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(run_pw_cycle())
        while True:
            print(f"[scheduler] Next run in {interval_min} minutes...")
            time.sleep(interval_min * 60)
            loop.run_until_complete(run_pw_cycle())
    else:
        run_xcrawl_cycle()
        while True:
            print(f"[scheduler] Next run in {interval_min} minutes...")
            time.sleep(interval_min * 60)
            run_xcrawl_cycle()


def main():
    use_pw = "--pw" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    interval = int(args[0]) if args else DEFAULT_INTERVAL_MIN

    def shutdown(sig, frame):
        print("\n[scheduler] Shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    run_scheduler(interval, use_pw=use_pw)


if __name__ == "__main__":
    main()
