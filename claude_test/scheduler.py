"""Scheduler: auto scrape+index posts every N minutes using Playwright."""

import asyncio
import os
import signal
import sys
import time

from dotenv import load_dotenv

load_dotenv()

DEFAULT_INTERVAL_MIN = 30


async def run_cycle():
    """Run one scrape + index cycle."""
    from pw_scraper import scrape_all
    from database import index_posts

    x_user = os.getenv("X_USERNAME", "")
    x_pass = os.getenv("X_PASSWORD", "")

    if not x_user or not x_pass:
        print("[scheduler] Error: Set X_USERNAME and X_PASSWORD in .env")
        return

    print(f"\n[scheduler] Starting cycle at {time.strftime('%H:%M:%S')}")
    try:
        posts = await scrape_all(x_user, x_pass, headless=True)
        if posts:
            index_posts(posts)
        else:
            print("[scheduler] No new posts collected.")
    except Exception as e:
        print(f"[scheduler] Error in cycle: {e}")


async def run_scheduler(interval_min: int = DEFAULT_INTERVAL_MIN):
    """Run the scrape → index cycle on a loop."""
    print(f"[scheduler] Auto-update every {interval_min} minutes. Press Ctrl+C to stop.")

    await run_cycle()

    while True:
        print(f"[scheduler] Next run in {interval_min} minutes...")
        await asyncio.sleep(interval_min * 60)
        await run_cycle()


def main():
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INTERVAL_MIN

    loop = asyncio.new_event_loop()

    def shutdown(sig, frame):
        print("\n[scheduler] Shutting down...")
        loop.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    loop.run_until_complete(run_scheduler(interval))


if __name__ == "__main__":
    main()
