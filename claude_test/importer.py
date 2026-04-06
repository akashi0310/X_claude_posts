"""Import XCrawl .json/.md exports into the pipeline."""

import json
import re
import sys
from pathlib import Path

from database import index_posts

EXPORTS_DIR = Path(__file__).parent / "exports"


def parse_xcrawl_json(file_path: Path) -> list[dict]:
    """Parse an XCrawl .json export into our post format."""
    with open(file_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    posts = []
    items = raw if isinstance(raw, list) else [raw]
    for item in items:
        posts.append({
            "id": str(item.get("id", item.get("url", ""))),
            "username": item.get("username", item.get("user", {}).get("username", "unknown")),
            "text": item.get("text", item.get("full_text", item.get("content", ""))),
            "date": item.get("date", item.get("created_at", "")),
            "likes": item.get("likes", item.get("favorite_count", 0)),
            "retweets": item.get("retweets", item.get("retweet_count", 0)),
            "replies": item.get("replies", item.get("reply_count", 0)),
            "url": item.get("url", ""),
            "source": "xcrawl_json",
        })
    return posts


def parse_xcrawl_md(file_path: Path) -> list[dict]:
    """Parse an XCrawl .md export into our post format.

    Expects markdown with posts separated by --- or ## headings.
    Each post block should have text content we can index.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by horizontal rules or h2 headings
    blocks = re.split(r"\n---+\n|\n## ", content)
    posts = []

    for i, block in enumerate(blocks):
        block = block.strip()
        if not block or len(block) < 10:
            continue

        # Try to extract username from @mentions
        username_match = re.search(r"@(\w+)", block)
        username = username_match.group(1) if username_match else "unknown"

        # Try to extract date
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", block)
        date = date_match.group(0) if date_match else ""

        posts.append({
            "id": f"xcrawl_md_{file_path.stem}_{i}",
            "username": username,
            "text": block,
            "date": date,
            "likes": 0,
            "retweets": 0,
            "replies": 0,
            "url": "",
            "source": "xcrawl_md",
        })

    return posts


def import_exports(directory: Path | None = None):
    """Import all .json and .md files from the exports directory."""
    directory = directory or EXPORTS_DIR
    if not directory.exists():
        print(f"[importer] Directory {directory} does not exist.")
        return

    all_posts = []

    for f in sorted(directory.iterdir()):
        if f.suffix == ".json":
            print(f"[importer] Parsing {f.name}...")
            posts = parse_xcrawl_json(f)
            print(f"[importer] Found {len(posts)} posts in {f.name}")
            all_posts.extend(posts)
        elif f.suffix == ".md":
            print(f"[importer] Parsing {f.name}...")
            posts = parse_xcrawl_md(f)
            print(f"[importer] Found {len(posts)} posts in {f.name}")
            all_posts.extend(posts)

    if not all_posts:
        print("[importer] No posts found. Drop .json or .md files into exports/")
        return

    print(f"[importer] Indexing {len(all_posts)} posts into Qdrant...")
    index_posts(all_posts)


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    import_exports(path)
