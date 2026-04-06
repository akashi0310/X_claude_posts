import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TWITTER_ACCOUNTS = os.getenv("TWITTER_ACCOUNTS", "DeRonin_,AnthropicAI,RLanceMartin,bcherny,HiTw93,hooeem,trq212").split(",")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "x_posts"
EMBEDDING_MODEL = "models/gemini-embedding-001"
GEMINI_MODEL = "models/gemini-2.5-flash"
