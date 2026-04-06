# X RAG Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the Streamlit frontend (`app.py`) to match the Pencil dark-mode dashboard design with sidebar, stats bar, chat area, and polished UI.

**Architecture:** Single-file Streamlit app with extensive custom CSS injected via `st.markdown`. Reuses existing backend functions from `agent.py`, `database.py`, `config.py`, and `xcrawl_scraper.py`. Also fixes `database.py` and `agent.py` to handle the simplified post format (text + url only, no likes/date fields).

**Tech Stack:** Streamlit 1.30+, Python, custom CSS, existing Qdrant + Gemini backend

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `claude_test/app.py` | Rewrite | Streamlit dashboard UI with custom dark theme CSS |
| `claude_test/database.py` | Modify (lines 85-87, 99-103) | Handle missing `date` field gracefully |
| `claude_test/agent.py` | Modify (lines 44-55, 69-80, 86-89) | Handle missing `likes`/`date` fields in search results and context builder |

---

### Task 1: Fix `database.py` for simplified post format

**Files:**
- Modify: `claude_test/database.py:85-87` (embedding text format)
- Modify: `claude_test/database.py:99-103` (Qdrant payload)

- [ ] **Step 1: Fix embedding text format to handle missing `date`**

In `claude_test/database.py`, change line 85-87 from:
```python
        texts = [
            f"@{p['username']} ({p['date']}): {p['text']}" for p in batch
        ]
```
to:
```python
        texts = [
            f"@{p['username']}{' (' + p['date'] + ')' if p.get('date') else ''}: {p['text']}" for p in batch
        ]
```

- [ ] **Step 2: Fix Qdrant payload to use `.get()` for optional fields**

In `claude_test/database.py`, change lines 99-103 from:
```python
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
```
to:
```python
                    payload={
                        "username": post["username"],
                        "text": post["text"],
                        "date": post.get("date", ""),
                        "likes": post.get("likes", 0),
                        "retweets": post.get("retweets", 0),
                        "replies": post.get("replies", 0),
                        "url": post.get("url", ""),
                        "source": post.get("source", ""),
                    },
```

- [ ] **Step 3: Verify the fix**

Run: `cd /c/Users/ADMIN/Documents/X_claude_posts/claude_test && ./venv/Scripts/python -c "from database import index_posts; print('import OK')"`
Expected: `import OK`

- [ ] **Step 4: Commit**

```bash
git add claude_test/database.py
git commit -m "fix: handle missing date/likes fields in database indexing"
```

---

### Task 2: Fix `agent.py` for simplified post format

**Files:**
- Modify: `claude_test/agent.py:44-55` (search_posts return)
- Modify: `claude_test/agent.py:69-80` (search_by_username return)
- Modify: `claude_test/agent.py:83-92` (build_context formatting)

- [ ] **Step 1: Fix `search_posts` to use `.get()` for optional fields**

In `claude_test/agent.py`, change lines 44-55 from:
```python
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
```
to:
```python
    return [
        {
            "username": r.payload.get("username", ""),
            "text": r.payload.get("text", ""),
            "date": r.payload.get("date", ""),
            "likes": r.payload.get("likes", 0),
            "retweets": r.payload.get("retweets", 0),
            "url": r.payload.get("url", ""),
            "score": r.score,
        }
        for r in results.points
    ]
```

- [ ] **Step 2: Fix `search_by_username` to use `.get()` for all fields**

In `claude_test/agent.py`, change lines 69-76 from:
```python
    for r in results[0]:
        posts.append({
            "username": r.payload["username"],
            "text": r.payload["text"],
            "date": r.payload["date"],
            "likes": r.payload.get("likes", 0),
            "retweets": r.payload.get("retweets", 0),
            "url": r.payload.get("url", ""),
        })
```
to:
```python
    for r in results[0]:
        posts.append({
            "username": r.payload.get("username", ""),
            "text": r.payload.get("text", ""),
            "date": r.payload.get("date", ""),
            "likes": r.payload.get("likes", 0),
            "retweets": r.payload.get("retweets", 0),
            "url": r.payload.get("url", ""),
        })
```

- [ ] **Step 3: Fix `build_context` to handle missing date/likes**

In `claude_test/agent.py`, change lines 86-91 from:
```python
    for i, p in enumerate(posts, 1):
        lines.append(
            f"[{i}] @{p['username']} ({p['date']}) [likes: {p['likes']}]\n"
            f"    {p['text']}\n"
            f"    {p['url']}"
        )
```
to:
```python
    for i, p in enumerate(posts, 1):
        date_str = f" ({p['date']})" if p.get("date") else ""
        likes_str = f" [likes: {p['likes']}]" if p.get("likes") else ""
        lines.append(
            f"[{i}] @{p['username']}{date_str}{likes_str}\n"
            f"    {p['text']}\n"
            f"    {p.get('url', '')}"
        )
```

- [ ] **Step 4: Verify the fix**

Run: `cd /c/Users/ADMIN/Documents/X_claude_posts/claude_test && ./venv/Scripts/python -c "from agent import build_context; print(build_context([{'username':'test','text':'hello','url':'https://x.com/test'}]))"`
Expected: `[1] @test` followed by the text and URL, no crash

- [ ] **Step 5: Commit**

```bash
git add claude_test/agent.py
git commit -m "fix: handle missing date/likes fields in agent search and context"
```

---

### Task 3: Rewrite `app.py` — Custom CSS and page config

**Files:**
- Rewrite: `claude_test/app.py`

- [ ] **Step 1: Write the custom CSS and page config section**

Replace the entire contents of `claude_test/app.py` with the following (this step covers imports, page config, CSS, and session state):

```python
"""X/Twitter RAG Agent — Dark Dashboard UI."""

import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from agent import ask, search_by_username
from config import TWITTER_ACCOUNTS
from database import ensure_collection, get_qdrant

# ---------- Page config ----------
st.set_page_config(
    page_title="X RAG Agent",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Custom CSS ----------
st.markdown("""
<style>
    /* --- Global dark theme --- */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #0A0A0A;
        color: #FFFFFF;
    }
    [data-testid="stHeader"] {
        background-color: #0A0A0A;
    }

    /* --- Sidebar --- */
    [data-testid="stSidebar"] {
        background-color: #18181b;
        border-right: 1px solid #2E2E2E;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] p,
    [data-testid="stSidebar"] label {
        color: #A1A1AA;
    }
    [data-testid="stSidebar"] .stTextInput input {
        background-color: #1A1A1A;
        border: 1px solid #2E2E2E;
        color: #FFFFFF;
        border-radius: 8px;
    }

    /* --- Sidebar buttons --- */
    [data-testid="stSidebar"] .stButton > button {
        background-color: transparent;
        color: #A1A1AA;
        border: none;
        border-radius: 8px;
        text-align: left;
        padding: 8px 12px;
        font-size: 14px;
        transition: background-color 0.2s;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #2E2E2E;
        color: #FFFFFF;
    }

    /* --- Stats bar --- */
    .stats-bar {
        display: flex;
        align-items: center;
        gap: 32px;
        padding: 20px 32px;
        border-bottom: 1px solid #2E2E2E;
        margin-bottom: 16px;
    }
    .stat-item {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    .stat-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        color: #A1A1AA;
        letter-spacing: 0.5px;
    }
    .stat-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 22px;
        font-weight: 700;
        color: #FFFFFF;
    }
    .stat-value.purple { color: #A855F7; }
    .stat-value.green { color: #22C55E; }
    .stat-divider {
        width: 1px;
        height: 32px;
        background-color: #2E2E2E;
    }

    /* --- Chat messages --- */
    [data-testid="stChatMessage"] {
        background-color: transparent;
        border: none;
        padding: 12px 0;
    }
    .user-msg {
        background-color: rgba(168, 85, 247, 0.1);
        border-radius: 12px;
        padding: 12px 16px;
        color: #FFFFFF;
        font-size: 14px;
        line-height: 1.6;
    }
    .bot-msg {
        background-color: #1A1A1A;
        border: 1px solid #2E2E2E;
        border-radius: 12px;
        padding: 12px 16px;
        color: #E4E4E7;
        font-size: 14px;
        line-height: 1.6;
    }
    .source-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: #71717A;
        margin-top: 8px;
    }

    /* --- Chat input --- */
    [data-testid="stChatInput"] textarea {
        background-color: #1A1A1A;
        border: 1px solid #2E2E2E;
        color: #FFFFFF;
        border-radius: 12px;
    }

    /* --- Crawl button --- */
    .crawl-btn > button {
        background-color: #A855F7 !important;
        color: #0A0A0A !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        padding: 8px 16px !important;
    }
    .crawl-btn > button:hover {
        background-color: #9333EA !important;
    }

    /* --- Active account highlight --- */
    .active-account > button {
        background-color: rgba(168, 85, 247, 0.1) !important;
        color: #FFFFFF !important;
    }

    /* --- Scrollbar --- */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0A0A0A; }
    ::-webkit-scrollbar-thumb { background: #2E2E2E; border-radius: 3px; }

    /* --- Hide Streamlit defaults --- */
    #MainMenu, footer, [data-testid="stToolbar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ---------- Qdrant connection ----------
try:
    client = get_qdrant()
    ensure_collection(client)
except Exception as e:
    st.error(f"Cannot connect to Qdrant: {e}\n\nRun: `docker compose up -d`")
    st.stop()

# ---------- Session state ----------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_filter" not in st.session_state:
    st.session_state.active_filter = None
```

- [ ] **Step 2: Verify syntax**

Run: `cd /c/Users/ADMIN/Documents/X_claude_posts/claude_test && ./venv/Scripts/python -c "import py_compile; py_compile.compile('app.py', doraise=True); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add claude_test/app.py
git commit -m "feat: add dark theme CSS and page config for dashboard redesign"
```

---

### Task 4: Rewrite `app.py` — Sidebar with account list

**Files:**
- Modify: `claude_test/app.py` (append after session state section)

- [ ] **Step 1: Add the sidebar section**

Append the following to the end of `claude_test/app.py`:

```python
# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### X RAG AGENT")

    search_query = st.text_input(
        "Search accounts",
        placeholder="Search accounts...",
        label_visibility="collapsed",
    )

    st.markdown(
        '<p style="font-family: monospace; font-size: 11px; color: #71717A; '
        'letter-spacing: 1px; margin: 16px 0 8px 0;">TRACKED ACCOUNTS</p>',
        unsafe_allow_html=True,
    )

    for account in TWITTER_ACCOUNTS:
        account = account.strip()
        if search_query and search_query.lower() not in account.lower():
            continue

        is_active = st.session_state.active_filter == account
        css_class = "active-account" if is_active else ""

        with st.container():
            st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
            if st.button(
                f"  @{account}",
                key=f"btn_{account}",
                use_container_width=True,
            ):
                if is_active:
                    st.session_state.active_filter = None
                else:
                    st.session_state.active_filter = account
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # Clear filter
    if st.session_state.active_filter:
        st.markdown("---")
        st.markdown(
            f'<p style="color: #A855F7; font-size: 13px;">'
            f'Filtered: @{st.session_state.active_filter}</p>',
            unsafe_allow_html=True,
        )
        if st.button("Clear filter", use_container_width=True):
            st.session_state.active_filter = None
            st.rerun()

    # Clear chat
    st.markdown("---")
    if st.button("Clear chat history", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
```

- [ ] **Step 2: Verify syntax**

Run: `cd /c/Users/ADMIN/Documents/X_claude_posts/claude_test && ./venv/Scripts/python -c "import py_compile; py_compile.compile('app.py', doraise=True); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add claude_test/app.py
git commit -m "feat: add sidebar with account list and search filter"
```

---

### Task 5: Rewrite `app.py` — Stats bar and chat interface

**Files:**
- Modify: `claude_test/app.py` (append after sidebar section)

- [ ] **Step 1: Add the stats bar**

Append the following to the end of `claude_test/app.py`:

```python
# ---------- Stats bar ----------
DATA_DIR = Path(__file__).parent / "data"
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
        last_updated = f"{int(delta.total_seconds() // 60)} min ago"
    elif delta.total_seconds() < 86400:
        last_updated = f"{int(delta.total_seconds() // 3600)}h ago"
    else:
        last_updated = mtime.strftime("%b %d")

active_count = len(TWITTER_ACCOUNTS)

st.markdown(f"""
<div class="stats-bar">
    <div class="stat-item">
        <span class="stat-label">Total Posts</span>
        <span class="stat-value">{total_posts:,}</span>
    </div>
    <div class="stat-divider"></div>
    <div class="stat-item">
        <span class="stat-label">Active Accounts</span>
        <span class="stat-value purple">{active_count}</span>
    </div>
    <div class="stat-divider"></div>
    <div class="stat-item">
        <span class="stat-label">Last Updated</span>
        <span class="stat-value green">{last_updated}</span>
    </div>
</div>
""", unsafe_allow_html=True)
```

- [ ] **Step 2: Add the chat interface**

Append the following to the end of `claude_test/app.py`:

```python
# ---------- Chat area ----------
if st.session_state.active_filter:
    st.caption(f"Filtered to **@{st.session_state.active_filter}**")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(
                f'<div class="user-msg">{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="bot-msg">{msg["content"]}</div>',
                unsafe_allow_html=True,
            )

# Chat input
if prompt := st.chat_input("Ask a question about the posts..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(
            f'<div class="user-msg">{prompt}</div>',
            unsafe_allow_html=True,
        )

    with st.chat_message("assistant"):
        with st.spinner("Searching and generating answer..."):
            try:
                response = ask(
                    question=prompt,
                    chat_history=st.session_state.messages[:-1],
                    username_filter=st.session_state.active_filter,
                )
            except Exception as e:
                response = f"Error: {e}"

        st.markdown(
            f'<div class="bot-msg">{response}</div>',
            unsafe_allow_html=True,
        )

    st.session_state.messages.append({"role": "assistant", "content": response})
```

- [ ] **Step 3: Verify syntax**

Run: `cd /c/Users/ADMIN/Documents/X_claude_posts/claude_test && ./venv/Scripts/python -c "import py_compile; py_compile.compile('app.py', doraise=True); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Run the app to verify visually**

Run: `cd /c/Users/ADMIN/Documents/X_claude_posts/claude_test && ./venv/Scripts/streamlit run app.py`
Expected: Browser opens with dark-themed dashboard matching the Pencil design

- [ ] **Step 5: Commit**

```bash
git add claude_test/app.py
git commit -m "feat: add stats bar and chat interface for dashboard redesign"
```

---

### Task 6: Final verification

- [ ] **Step 1: Run full app and verify all sections**

Run: `cd /c/Users/ADMIN/Documents/X_claude_posts/claude_test && ./venv/Scripts/streamlit run app.py`

Verify:
- Dark background (#0A0A0A) across the entire page
- Sidebar shows "X RAG AGENT" title, search input, 7 account buttons with purple highlight on active
- Stats bar shows Total Posts count, Active Accounts (7), Last Updated timestamp
- Chat input at the bottom accepts questions
- Bot responses appear in dark card with border
- User messages appear with purple tint background

- [ ] **Step 2: Test account filtering**

Click an account in the sidebar (e.g., @AnthropicAI). Verify:
- The button highlights with purple tint
- The "Filtered to @AnthropicAI" caption appears
- Clicking again clears the filter

- [ ] **Step 3: Test chat interaction**

Type a question like "What posts are available?" and press Enter. Verify:
- User message appears in purple bubble
- Bot response appears in dark card
- No crashes from missing date/likes fields

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete X RAG dashboard redesign with dark theme"
```
