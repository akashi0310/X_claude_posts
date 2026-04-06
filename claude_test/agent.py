"""RAG chat agent: question → embed → Qdrant search → Gemini Flash answer."""

from datetime import datetime

import google.generativeai as genai
from qdrant_client.models import FieldCondition, Filter, MatchValue

from config import COLLECTION_NAME, GEMINI_API_KEY, GEMINI_MODEL
from database import embed_texts, get_qdrant

SYSTEM_PROMPT = """You are an AI assistant that answers questions based on recent X/Twitter posts
from specific accounts. Use the provided context (retrieved posts) to answer the user's question.

Rules:
- Only use information from the provided posts. If the posts don't contain relevant info, say so.
- Cite the @username and date when referencing a specific post.
- Be concise and direct.
- If asked about opinions or takes, present them as "According to @username..." not as facts.
- You receive the full conversation history. Use it to understand follow-up questions.
  For example, if the user asks "what about the more previous?" after asking about yesterday,
  understand they mean the day before yesterday.
- When the user says "today", "yesterday", etc., interpret relative to the current date provided.
- If a sidebar filter is active (shown as "ACTIVE FILTER"), scope your answers to that account only.
"""


def search_posts(query: str, top_k: int = 10, username_filter: str | None = None) -> list[dict]:
    """Embed query and search Qdrant for relevant posts, optionally filtered by username."""
    query_vector = embed_texts([query])[0]
    client = get_qdrant()

    search_filter = None
    if username_filter:
        search_filter = Filter(
            must=[FieldCondition(key="username", match=MatchValue(value=username_filter))]
        )

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=search_filter,
        limit=top_k,
    )
    return [
        {
            "username": r.payload["username"],
            "text": r.payload["text"],
            "date": r.payload["date"],
            "likes": r.payload.get("likes", 0),
            "retweets": r.payload.get("retweets", 0),
            "url": r.payload.get("url", ""),
            "score": r.score,
        }
        for r in results.points
    ]


def search_by_username(username: str, top_k: int = 20) -> list[dict]:
    """Search all posts from a specific username (for sidebar preview)."""
    client = get_qdrant()
    results = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[FieldCondition(key="username", match=MatchValue(value=username))]
        ),
        limit=top_k,
    )
    posts = []
    for r in results[0]:
        posts.append({
            "username": r.payload["username"],
            "text": r.payload["text"],
            "date": r.payload["date"],
            "likes": r.payload.get("likes", 0),
            "retweets": r.payload.get("retweets", 0),
            "url": r.payload.get("url", ""),
        })
    # Sort by date descending
    posts.sort(key=lambda x: x["date"], reverse=True)
    return posts


def build_context(posts: list[dict]) -> str:
    """Format retrieved posts as context for the LLM."""
    lines = []
    for i, p in enumerate(posts, 1):
        lines.append(
            f"[{i}] @{p['username']} ({p['date']}) [likes: {p['likes']}]\n"
            f"    {p['text']}\n"
            f"    {p['url']}"
        )
    return "\n\n".join(lines)


def format_chat_history(history: list[dict]) -> str:
    """Format conversation history for the LLM."""
    lines = []
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def ask(
    question: str,
    chat_history: list[dict] | None = None,
    username_filter: str | None = None,
    top_k: int = 10,
) -> str:
    """Full RAG pipeline with conversation history and optional username filter."""
    genai.configure(api_key=GEMINI_API_KEY)

    # Build a search query that incorporates conversation context
    search_query = question
    if username_filter:
        search_query = f"@{username_filter} {question}"

    # Retrieve relevant posts
    posts = search_posts(search_query, top_k=top_k, username_filter=username_filter)
    if not posts:
        return "No relevant posts found in the database. Try collecting some posts first."

    context = build_context(posts)

    # Build conversation history string
    history_str = ""
    if chat_history:
        history_str = f"\n**Conversation History:**\n{format_chat_history(chat_history)}\n"

    # Active filter info
    filter_str = ""
    if username_filter:
        filter_str = f"\n**ACTIVE FILTER:** Only showing posts from @{username_filter}\n"

    # Generate answer with Gemini Flash
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
    )
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""Current date: {today}
{filter_str}{history_str}
Based on the following X/Twitter posts, answer this question:

**Question:** {question}

**Retrieved Posts:**
{context}

**Answer:**"""

    response = model.generate_content(prompt)
    return response.text


def chat():
    """Interactive chat loop with history."""
    print("=" * 60)
    print("  X/Twitter RAG Agent")
    print("  Ask questions about tracked accounts' posts.")
    print("  Type 'quit' to exit.")
    print("=" * 60)

    history = []
    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        print("\nSearching and generating answer...\n")
        answer = ask(question, chat_history=history)
        print(f"Agent: {answer}")

        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    chat()
