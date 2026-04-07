"""X/Twitter RAG Agent — Flask Web App."""

from flask import Flask, jsonify, render_template, request

from agent import ask, search_by_username
from config import TWITTER_ACCOUNTS
from database import get_supabase

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    client = get_supabase()

    # Get total post count from Supabase
    result = client.table("x_posts").select("id", count="exact").execute()
    total_posts = result.count or 0

    # Get the most recent post date for "last updated"
    last_updated = "Never"
    latest = client.table("x_posts").select("date").order("date", desc=True).limit(1).execute()
    if latest.data and latest.data[0].get("date"):
        from datetime import datetime
        try:
            last_date = datetime.fromisoformat(latest.data[0]["date"].replace("Z", "+00:00"))
            now = datetime.now(last_date.tzinfo) if last_date.tzinfo else datetime.now()
            delta = now - last_date
            if delta.total_seconds() < 60:
                last_updated = "Just now"
            elif delta.total_seconds() < 3600:
                last_updated = f"{int(delta.total_seconds() // 60)}m ago"
            elif delta.total_seconds() < 86400:
                last_updated = f"{int(delta.total_seconds() // 3600)}h ago"
            else:
                last_updated = last_date.strftime("%b %d")
        except (ValueError, TypeError):
            last_updated = latest.data[0]["date"][:10]

    return jsonify({
        "total_posts": total_posts,
        "active_accounts": len(TWITTER_ACCOUNTS),
        "last_updated": last_updated,
        "accounts": [a.strip() for a in TWITTER_ACCOUNTS],
    })


@app.route("/api/posts")
def api_posts():
    username = request.args.get("username")
    limit = request.args.get("limit", 30, type=int)
    posts = search_by_username(username if username else None, top_k=limit)
    return jsonify({"posts": posts})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    question = data.get("question", "")
    history = data.get("history", [])
    username_filter = data.get("username_filter")

    if not question:
        return jsonify({"answer": "Please ask a question."}), 400

    answer = ask(
        question=question,
        chat_history=history if history else None,
        username_filter=username_filter if username_filter else None,
    )
    return jsonify({"answer": answer})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
