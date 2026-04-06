"""Streamlit UI for X/Twitter RAG Agent."""

import streamlit as st

from agent import ask, search_by_username
from config import TWITTER_ACCOUNTS
from database import ensure_collection, get_qdrant

# ---------- Page config ----------
st.set_page_config(
    page_title="X/Twitter RAG Agent",
    page_icon="🐦",
    layout="wide",
)

# ---------- Ensure Qdrant collection exists ----------
try:
    client = get_qdrant()
    ensure_collection(client)
except Exception as e:
    st.error(f"⚠️ Cannot connect to Qdrant: {e}\n\nMake sure Qdrant is running: `docker compose up -d`")
    st.stop()

# ---------- Session state init ----------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_filter" not in st.session_state:
    st.session_state.active_filter = None
if "sidebar_results" not in st.session_state:
    st.session_state.sidebar_results = []

# ---------- Sidebar: Search & Filter ----------
with st.sidebar:
    st.header("🔍 Search & Filter")

    search_query = st.text_input(
        "Search by account",
        placeholder="e.g. AnthropicAI",
        help="Type a username to filter posts and scope the chat agent to that account.",
    )

    # Quick filter buttons
    st.markdown("**Quick filters:**")
    cols = st.columns(3)
    for i, account in enumerate(TWITTER_ACCOUNTS):
        col = cols[i % 3]
        if col.button(f"@{account}", key=f"btn_{account}", use_container_width=True):
            search_query = account
            st.session_state.active_filter = account

    # Apply search
    if search_query:
        search_query = search_query.strip().lstrip("@")
        st.session_state.active_filter = search_query

        try:
            results = search_by_username(search_query, top_k=20)
            st.session_state.sidebar_results = results
        except Exception as e:
            st.error(f"Search error: {e}")
            st.session_state.sidebar_results = []

    # Clear filter
    if st.session_state.active_filter:
        st.markdown(f"**Active filter:** `@{st.session_state.active_filter}`")
        if st.button("✕ Clear filter", use_container_width=True):
            st.session_state.active_filter = None
            st.session_state.sidebar_results = []
            st.rerun()

    # Show search results
    if st.session_state.sidebar_results:
        st.divider()
        st.subheader(f"Posts from @{st.session_state.active_filter}")
        for post in st.session_state.sidebar_results:
            with st.container():
                st.markdown(
                    f"**@{post['username']}** · {post['date']}  \n"
                    f"{post['text'][:200]}{'...' if len(post['text']) > 200 else ''}  \n"
                    f"❤️ {post['likes']}  🔁 {post.get('retweets', 0)}"
                )
                if post.get("url"):
                    st.markdown(f"[View post]({post['url']})")
                st.divider()
    elif st.session_state.active_filter:
        st.info("No posts found for this account. Try collecting posts first.")

    # Clear chat button
    st.markdown("---")
    if st.button("🗑️ Clear chat history", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ---------- Main: Chat Interface ----------
st.title("🐦 X/Twitter RAG Agent")

if st.session_state.active_filter:
    st.caption(f"🔎 Filtered to **@{st.session_state.active_filter}** — questions will be scoped to this account.")
else:
    st.caption("Ask anything about tracked accounts' posts. Use the sidebar to filter by account.")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask a question about the posts..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Searching posts and generating answer..."):
            try:
                response = ask(
                    question=prompt,
                    chat_history=st.session_state.messages[:-1],  # history before this message
                    username_filter=st.session_state.active_filter,
                )
            except Exception as e:
                response = f"Error: {e}"

        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
