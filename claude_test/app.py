"""X/Twitter RAG Agent — Flask Web App."""

import json
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from agent import ask, search_by_username
from config import TWITTER_ACCOUNTS

app = Flask(__name__)

DATA_DIR = Path(__file__).parent / "data"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    posts_file = DATA_DIR / "posts.json"
    total_posts = 0
    if posts_file.exists():
        try:
            with open(posts_file, "r", encoding="utf-8") as f:
                total_posts = len(json.load(f))
        except (json.JSONDecodeError, IOError):
            pass

    last_updated = "Never"
    if posts_file.exists():
        mtime = datetime.fromtimestamp(posts_file.stat().st_mtime)
        delta = datetime.now() - mtime
        if delta.total_seconds() < 60:
            last_updated = "Just now"
        elif delta.total_seconds() < 3600:
            last_updated = f"{int(delta.total_seconds() // 60)}m ago"
        elif delta.total_seconds() < 86400:
            last_updated = f"{int(delta.total_seconds() // 3600)}h ago"
        else:
            last_updated = mtime.strftime("%b %d")

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
