"""RAG chat agent: question → embed → Supabase vector search → Gemini Flash answer."""

from datetime import datetime

import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL
from database import embed_texts, get_supabase

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
    """Embed query and search Supabase for relevant posts, optionally filtered by username."""
    query_vector = embed_texts([query])[0]
    client = get_supabase()

    result = client.rpc("match_posts", {
        "query_embedding": query_vector,
        "match_count": top_k,
        "filter_username": username_filter,
    }).execute()

    return [
        {
            "username": r.get("username", ""),
            "text": r.get("text", ""),
            "date": r.get("date", ""),
            "likes": r.get("likes", 0),
            "retweets": r.get("retweets", 0),
            "url": r.get("url", ""),
            "score": r.get("similarity", 0),
        }
        for r in result.data
    ]


def search_by_username(username: str | None = None, top_k: int = 20) -> list[dict]:
    """Search posts, optionally filtered by username (for sidebar preview)."""
    client = get_supabase()
    query = client.table("x_posts").select("username, text, date, likes, retweets, url")
    if username:
        query = query.eq("username", username)
    result = query.order("date", desc=True).limit(top_k).execute()
    return result.data


def build_context(posts: list[dict]) -> str:
    """Format retrieved posts as context for the LLM."""
    lines = []
    for i, p in enumerate(posts, 1):
        date_str = f" ({p['date']})" if p.get("date") else ""
        likes_str = f" [likes: {p['likes']}]" if p.get("likes") else ""
        lines.append(
            f"[{i}] @{p['username']}{date_str}{likes_str}\n"
            f"    {p['text']}\n"
            f"    {p.get('url', '')}"
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

    search_query = question
    if username_filter:
        search_query = f"@{username_filter} {question}"

    posts = search_posts(search_query, top_k=top_k, username_filter=username_filter)
    if not posts:
        return "No relevant posts found in the database. Try collecting some posts first."

    context = build_context(posts)

    history_str = ""
    if chat_history:
        history_str = f"\n**Conversation History:**\n{format_chat_history(chat_history)}\n"

    filter_str = ""
    if username_filter:
        filter_str = f"\n**ACTIVE FILTER:** Only showing posts from @{username_filter}\n"

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
