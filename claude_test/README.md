# X RAG Agent

A RAG-powered app that scrapes X/Twitter posts from tracked accounts, stores them with vector embeddings in Supabase, and lets you search and ask questions about them using AI.

## Setup

### 1. Install Python dependencies

```bash
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate

# Then install
pip install -r requirements.txt
playwright install
```

### 2. Configure `.env`

Create a `.env` file in this folder:

```
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
TWITTER_ACCOUNTS=DeRonin_,AnthropicAI,HiTw93,hooeem,trq212
X_USERNAME=your_x_email
X_PASSWORD=your_x_password
```

- **GEMINI_API_KEY**: Get from https://aistudio.google.com/apikey
- **SUPABASE_URL / KEY**: Get from your Supabase project → Settings → API
- **TWITTER_ACCOUNTS**: Comma-separated X handles to track
- **X_USERNAME / X_PASSWORD**: Your X/Twitter login (for Playwright scraper)

### 3. Set up Supabase database

In your Supabase dashboard, go to **SQL Editor** and run:

```sql
create extension if not exists vector;

create table x_posts (
  id text primary key,
  username text not null,
  text text not null,
  date text default '',
  likes int default 0,
  retweets int default 0,
  replies int default 0,
  url text default '',
  source text default '',
  embedding vector(768)
);

create index on x_posts using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create or replace function match_posts(
  query_embedding vector(768),
  match_count int default 10,
  filter_username text default null
)
returns table (
  id text, username text, text text, date text,
  likes int, retweets int, replies int,
  url text, source text, similarity float
)
language plpgsql as $$
begin
  return query
  select
    x.id, x.username, x.text, x.date, x.likes,
    x.retweets, x.replies, x.url, x.source,
    1 - (x.embedding <=> query_embedding) as similarity
  from x_posts x
  where (filter_username is null or x.username = filter_username)
  order by x.embedding <=> query_embedding
  limit match_count;
end;
$$;
```

### 4. Log in to X (first time only)

```bash
python login_once.py
```

A browser window opens. Log in to your X/Twitter account manually, then close it. This saves your session to `chrome_profile/` so the scraper can use it without logging in every time.

## Usage

### Scrape posts

```bash
# Scrape with visible browser (recommended for first run)
python main.py scrape --pw-head

# Scrape headless (no browser window)
python main.py scrape --pw
```

Takes ~2-5 minutes for 7 accounts. Posts are saved to `data/posts.json`.

### Index posts into Supabase

```bash
python main.py index
```

Embeds all posts and stores them in Supabase with vector embeddings. Takes ~1-2 minutes for 300 posts.

### Run the web app

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

- **Feed tab**: Browse latest posts from all tracked accounts
- **Chat tab**: Ask questions about the posts using AI
- **Filter chips**: Click an account name to filter posts and chat to that account

### Auto-scrape on a schedule

```bash
# Scrape + index every 30 minutes
python main.py schedule --pw 30

# Custom interval (every 10 minutes)
python main.py schedule --pw 10
```

This runs in a loop — use a separate terminal for the web app.

### CLI chat (no web app needed)

```bash
# Interactive chat
python main.py chat

# One-shot question
python main.py ask "what did DeRonin_ post about AI?"
```

### Import exported data

```bash
# Import .json or .md files from exports/ folder
python main.py import
```

## Adding new accounts to track

Edit the `TWITTER_ACCOUNTS` line in `.env`:

```
TWITTER_ACCOUNTS=DeRonin_,AnthropicAI,HiTw93,hooeem,trq212,NewUser1,NewUser2
```

Then scrape and index the new data:

```bash
python main.py scrape --pw-head
python main.py index
```

Restart the Flask app (`python app.py`) to see the new account chips.

## File Structure

```
├── app.py              # Flask web app
├── templates/
│   └── index.html      # Frontend (HTML/CSS/JS)
├── agent.py            # RAG search + Gemini answer generation
├── database.py         # Supabase + Gemini embedding layer
├── config.py           # Environment config
├── main.py             # CLI entry point
├── pw_scraper.py       # Playwright browser scraper
├── xcrawl_scraper.py   # XCrawl API scraper
├── collector.py        # twscrape + RSS fallback scraper
├── scheduler.py        # Auto scrape+index scheduler
├── login_once.py       # One-time X login helper
├── data/
│   └── posts.json      # Scraped posts cache
└── chrome_profile/     # Saved browser session
```
