import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TWITTER_ACCOUNTS = os.getenv("TWITTER_ACCOUNTS", "DeRonin_,AnthropicAI,RLanceMartin,bcherny,HiTw93,hooeem,trq212").split(",")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIM = 768
GEMINI_MODEL = "models/gemini-2.5-flash"
