"""Embed posts with Gemini and store in Qdrant."""

import json
import re
import time
import uuid
from pathlib import Path

import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from config import (
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    GEMINI_API_KEY,
    QDRANT_HOST,
    QDRANT_PORT,
)

DATA_DIR = Path(__file__).parent / "data"


def get_qdrant() -> QdrantClient:
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_collection(client: QdrantClient, dim: int = 3072):
    """Create collection if it doesn't exist."""
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        print(f"[qdrant] Created collection '{COLLECTION_NAME}'")
    else:
        print(f"[qdrant] Collection '{COLLECTION_NAME}' already exists")


def embed_texts(texts: list[str], max_retries: int = 5) -> list[list[float]]:
    """Embed a batch of texts using Gemini Embedding API with retry on rate limit."""
    genai.configure(api_key=GEMINI_API_KEY)
    for attempt in range(max_retries):
        try:
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=texts,
            )
            return result["embedding"]
        except Exception as e:
            error_str = str(e)
            if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                # Try to parse the retry delay from the error message
                match = re.search(r"Please retry in ([\d.]+)s", error_str)
                wait = float(match.group(1)) if match else 30 * (2 ** attempt)
                print(f"[embedder] Rate limited. Waiting {wait:.1f}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Embedding failed after {max_retries} retries due to rate limiting.")


def index_posts(posts: list[dict] | None = None, batch_size: int = 50):
    """Embed and store posts in Qdrant."""
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

    client = get_qdrant()
    ensure_collection(client)

    # Process in batches
    total = 0
    for i in range(0, len(posts), batch_size):
        batch = posts[i : i + batch_size]
        texts = [
            f"@{p['username']} ({p['date']}): {p['text']}" for p in batch
        ]

        print(f"[embedder] Embedding batch {i // batch_size + 1} ({len(batch)} posts)...")
        vectors = embed_texts(texts)

        points = []
        for post, vector in zip(batch, vectors):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, post["id"]))
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "username": post["username"],
                        "text": post["text"],
                        "date": post["date"],
                        "likes": post.get("likes", 0),
                        "retweets": post.get("retweets", 0),
                        "replies": post.get("replies", 0),
                        "url": post.get("url", ""),
                        "source": post.get("source", ""),
                    },
                )
            )

        client.upsert(collection_name=COLLECTION_NAME, points=points)
        total += len(points)
        print(f"[embedder] Indexed {total}/{len(posts)} posts")

        # Pause between batches to stay within free tier rate limits
        if i + batch_size < len(posts):
            time.sleep(2)

    print(f"[embedder] Done. {total} posts indexed in Qdrant.")


if __name__ == "__main__":
    index_posts()
