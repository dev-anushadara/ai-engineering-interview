import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agent_social.db")
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.4"))
