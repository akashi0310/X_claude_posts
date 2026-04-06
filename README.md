# X/Twitter RAG Agent

A Retrieval-Augmented Generation (RAG) system that scrapes X/Twitter posts from tracked accounts, indexes them into a vector database, and lets you ask natural language questions about the collected content.

## How It Works

1. **Scrape** posts from X/Twitter using the XCrawl API or Playwright browser automation
2. **Embed & Index** posts into a Qdrant vector database using Google's Gemini embedding model
3. **Chat** with an AI agent (Gemini 2.5 Flash) that retrieves relevant posts and answers your questions with citations

## Architecture

| Component | Description |
|---|---|
| `main.py` | CLI entry point for all commands |
| `app.py` | Streamlit web UI with chat interface and sidebar filtering |
| `agent.py` | RAG pipeline: embed query → Qdrant search → Gemini answer |
| `xcrawl_scraper.py` | Scrapes X/Twitter via XCrawl API (AI-powered extraction) |
| `collector.py` | Alternative scraper using twscrape + RSS fallback |
| `importer.py` | Imports exported `.json`/`.md` files into the pipeline |
| `scheduler.py` | Automated scrape+index loop on a configurable interval |
| `config.py` | Central configuration (API keys, accounts, models) |

## Prerequisites

- Python 3.12+
- Docker (for Qdrant)
- API keys: **Gemini API** and **XCrawl API** (or X/Twitter credentials for Playwright scraping)

## Setup

1. **Start Qdrant:**
   ```bash
   docker compose up -d
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables** in a `.env` file:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   XCRAWL_API_KEY=your_xcrawl_api_key

   # Optional: for Playwright scraping
   X_USERNAME=your_x_username
   X_PASSWORD=your_x_password

   # Optional: customize tracked accounts (comma-separated)
   TWITTER_ACCOUNTS=DeRonin_,AnthropicAI,RLanceMartin,bcherny,HiTw93,hooeem,trq212
   ```

## Usage

### CLI

```bash
# Scrape posts using XCrawl API (recommended)
python main.py scrape

# Scrape using Playwright (headless)
python main.py scrape --pw

# Scrape using Playwright (visible browser)
python main.py scrape --pw-head

# Import exported .json/.md files from exports/
python main.py import

# Embed & index posts into Qdrant
python main.py index

# Interactive chat
python main.py chat

# One-shot question
python main.py ask "What did AnthropicAI post about recently?"

# Auto scrape+index every N minutes (default: 30)
python main.py schedule 15
```

### Web UI

```bash
streamlit run app.py
```

The Streamlit app provides:
- Chat interface with conversation history
- Sidebar with quick account filters
- Post previews with likes, retweets, and links to originals
