# X RAG Agent — Flask Frontend Design Spec

## Context
Replace Streamlit dashboard with a custom Flask + vanilla HTML/CSS/JS frontend inspired by theclaudecode.xyz. The current Streamlit app (app.py) provides a chat interface and post browsing but lacks visual polish and flexibility. The new frontend will have a modern dark theme with orange accents and a tabbed layout separating Feed browsing from Chat Q&A.

## Architecture

### Tech Stack
- **Backend**: Flask (Python) — serves HTML and JSON API endpoints
- **Frontend**: Single HTML page with vanilla CSS and JS — no build tools, no npm
- **Existing code reused**: `agent.py` (search_posts, search_by_username, ask), `database.py` (get_supabase, embed_texts), `config.py`

### Files
- `app.py` — **rewrite** — Flask app replacing Streamlit, serves static files + API
- `templates/index.html` — **new** — single-page app with all HTML/CSS/JS
- `requirements.txt` — **update** — replace `streamlit` with `flask`

## API Endpoints

### `GET /api/posts`
- Query params: `username` (optional), `limit` (optional, default 30)
- Returns: `{ "posts": [{ username, text, date, likes, retweets, replies, url }] }`
- Source: calls `search_by_username(username, top_k=limit)`

### `POST /api/chat`
- Body: `{ "question": str, "history": [{ role, content }], "username_filter": str|null }`
- Returns: `{ "answer": str }`
- Source: calls `ask(question, chat_history, username_filter)`

### `GET /api/stats`
- Returns: `{ "total_posts": int, "active_accounts": int, "last_updated": str, "accounts": [str] }`
- Source: queries Supabase count + config TWITTER_ACCOUNTS + posts.json mtime

## UI Design

### Theme
- Background: `#0a0a0a`
- Surface: `rgba(255,255,255,0.02)` with `border: 1px solid rgba(255,255,255,0.08)`
- Primary accent: `#FF6B35` (orange/coral)
- Text primary: `#ffffff`, secondary: `#a1a1aa`, muted: `#71717a`
- Success: `#22c55e`
- Headings: Georgia serif
- Body: system sans-serif

### Navigation Bar (fixed top)
**Row 1:**
- Left: Logo "X RAG Agent" (Georgia, 20px, orange, bold)
- Center-left: Tab links "Feed" and "Chat" — active tab has `background: rgba(255,107,53,0.15); color: #FF6B35`
- Right: Stats — "310 posts · 7 accounts" + "Updated 5m ago" (green)

**Row 2:**
- Horizontally scrollable account filter chips
- Inactive: `border: 1px solid rgba(255,255,255,0.1); color: #a1a1aa`
- Active: `border-color: rgba(255,107,53,0.4); background: rgba(255,107,53,0.1); color: #FF6B35`
- Click to toggle filter, click again to deselect

### Feed Tab
- 3-column responsive grid (2 on tablet, 1 on mobile)
- **Post cards** (compact):
  - Avatar: 28px circle with gradient background, first letter of username
  - Header: @username (white, 13px, bold) + date (gray, 11px, right-aligned)
  - Body: post text, 13px, 3-line clamp
  - Footer: "59 likes · 7 RTs" (gray) + "View →" link (orange, opens X in new tab)
  - Card: `border-radius: 12px; padding: 16px`
  - Hover: border color shifts to `rgba(255,107,53,0.3)`
- Loads latest 30 posts on page load, filtered by active account chip
- Pagination or "Load more" button at bottom

### Chat Tab
- Full-height chat area with messages + fixed input bar at bottom
- **User messages**: right-aligned, `background: rgba(255,107,53,0.1); border: 1px solid rgba(255,107,53,0.2)`, rounded bubble (16px radius, 4px bottom-right)
- **Assistant messages**: left-aligned, `background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08)`, rounded bubble (16px radius, 4px bottom-left)
- **Input bar**: bottom-fixed, dark input with 12px border-radius, orange send button (32px square, "↑" icon)
- Account filter from nav applies — shown as "Filtering: @username" indicator
- Chat history maintained in JS (array of {role, content}), sent with each request

## Behavior
- Tab switching is client-side (show/hide divs), no page reload
- Account chip filter applies to both Feed and Chat
- Feed auto-refreshes posts when chip filter changes (fetch API call)
- Chat sends full history for context-aware follow-ups
- Loading states: skeleton pulse on feed cards, "Thinking..." indicator on chat

## Verification
1. `pip install flask` (in venv)
2. `python app.py` — should start on http://localhost:5000
3. Feed tab: shows 30 latest posts in 3-column grid
4. Click account chip: feed filters to that account
5. Chat tab: ask a question, get RAG answer with sources
6. Chat with filter: answers scoped to selected account
7. Responsive: works on mobile width (1 column)
