"""
Sound Design RAG - Configuration.

Reads settings from environment variables with .env file support.
"""
import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.absolute()

# Load .env file for local development
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# --- LLM Settings ---
# Checks .env first, then common env vars, then falls back to empty
LLM_API_KEY = (
    os.getenv("LLM_API_KEY")
    or os.getenv("DEEPSEEK_API_KEY")
    or os.getenv("NVIDIA_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or os.getenv("OPENROUTER_API_KEY")
    or ""
)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# --- Embedding Settings ---
# "local" = ChromaDB built-in ONNX all-MiniLM-L6-v2 (no API key needed)
# "api"   = OpenAI-compatible embedding API (e.g. text-embedding-3-small)
EMBEDDING_MODE = os.getenv("EMBEDDING_MODE", "local")

EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", LLM_API_KEY)
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", LLM_BASE_URL)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# --- PDF Data ---
PDF_DIR = Path(os.getenv("PDF_DIR", str(PROJECT_ROOT / "data")))
CHROMA_DB_DIR = Path(os.getenv("CHROMA_DB_DIR", str(PROJECT_ROOT / "chroma_db")))

# --- Chunking ---
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# --- Server ---
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "7860"))
