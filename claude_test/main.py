"""
X/Twitter RAG Agent - Main Entry Point

Usage:
    python main.py scrape            # Scrape posts with XCrawl API (recommended)
    python main.py scrape --pw       # Scrape with Playwright browser instead
    python main.py scrape --pw-head  # Playwright with visible browser
    python main.py import            # Import exported .json/.md from exports/
    python main.py index             # Embed & index posts.json into Qdrant
    python main.py chat              # Interactive Q&A with the RAG agent
    python main.py ask "question"    # One-shot question
    python main.py schedule [N]      # Auto scrape+index every N minutes (default: 30)
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def print_help():
    print(__doc__)


def main():
    if len(sys.argv) < 2:
        print_help()
        return

    cmd = sys.argv[1].lower()

    if cmd == "scrape":
        from database import index_posts

        if "--pw" in sys.argv or "--pw-head" in sys.argv:
            # Playwright scraper
            from pw_scraper import scrape_all as pw_scrape
            x_user = os.getenv("X_USERNAME", "")
            x_pass = os.getenv("X_PASSWORD", "")
            if not x_user or not x_pass:
                print("Error: Set X_USERNAME and X_PASSWORD in your .env file")
                return
            headless = "--pw-head" not in sys.argv
            posts = asyncio.run(pw_scrape(x_user, x_pass, headless=headless))
        else:
            # XCrawl API (default)
            from xcrawl_scraper import scrape_all as xc_scrape
            posts = xc_scrape()

        if posts:
            print(f"\n[main] Scraping done. Now indexing {len(posts)} posts into Qdrant...")
            index_posts(posts)
        else:
            print("[main] No posts collected.")

    elif cmd == "import":
        from importer import import_exports
        from pathlib import Path
        path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
        import_exports(path)

    elif cmd == "index":
        from database import index_posts
        index_posts()

    elif cmd == "chat":
        from agent import chat
        chat()

    elif cmd == "ask":
        if len(sys.argv) < 3:
            print("Usage: python main.py ask \"your question here\"")
            return
        from agent import ask
        question = " ".join(sys.argv[2:])
        answer = ask(question)
        print(f"\n{answer}")

    elif cmd == "schedule":
        from scheduler import main as scheduler_main
        scheduler_main()

    else:
        print(f"Unknown command: {cmd}")
        print_help()


if __name__ == "__main__":
    main()
