"""Embed posts with Gemini and store in Supabase (pgvector)."""

import json
import re
import time
from pathlib import Path

import google.generativeai as genai
from supabase import create_client

from config import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    GEMINI_API_KEY,
    SUPABASE_KEY,
    SUPABASE_URL,
)

DATA_DIR = Path(__file__).parent / "data"


def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def embed_texts(texts: list[str], max_retries: int = 5) -> list[list[float]]:
    """Embed a batch of texts using Gemini Embedding API with retry on rate limit."""
    genai.configure(api_key=GEMINI_API_KEY)
    for attempt in range(max_retries):
        try:
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=texts,
                output_dimensionality=EMBEDDING_DIM,
            )
            return result["embedding"]
        except Exception as e:
            error_str = str(e)
            if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                match = re.search(r"Please retry in ([\d.]+)s", error_str)
                wait = float(match.group(1)) if match else 30 * (2 ** attempt)
                print(f"[embedder] Rate limited. Waiting {wait:.1f}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Embedding failed after {max_retries} retries due to rate limiting.")


def index_posts(posts: list[dict] | None = None, batch_size: int = 50):
    """Embed and store posts in Supabase."""
    if posts is None:
        posts_path = DATA_DIR / "posts.json"
        if not posts_path.exists():
            print("[embedder] No posts.json found. Run scraper first.")
            return
        with open(posts_path, "r", encoding="utf-8") as f:
            posts = json.load(f)

    if not posts:
        print("[embedder] No posts to index.")
        return

    client = get_supabase()

    total = 0
    for i in range(0, len(posts), batch_size):
        batch = posts[i : i + batch_size]
        texts = [
            f"@{p['username']}{' (' + p['date'] + ')' if p.get('date') else ''}: {p['text']}" for p in batch
        ]

        print(f"[embedder] Embedding batch {i // batch_size + 1} ({len(batch)} posts)...")
        vectors = embed_texts(texts)

        rows = []
        for post, vector in zip(batch, vectors):
            rows.append({
                "id": post["id"],
                "username": post["username"],
                "text": post["text"],
                "date": post.get("date", ""),
                "likes": post.get("likes", 0),
                "retweets": post.get("retweets", 0),
                "replies": post.get("replies", 0),
                "url": post.get("url", ""),
                "source": post.get("source", ""),
                "embedding": vector,
            })

        client.table("x_posts").upsert(rows).execute()
        total += len(rows)
        print(f"[embedder] Indexed {total}/{len(posts)} posts")

        if i + batch_size < len(posts):
            time.sleep(2)

    print(f"[embedder] Done. {total} posts indexed in Supabase.")


if __name__ == "__main__":
    index_posts()
