---
title: Sound Design RAG
emoji: 🎛️
colorFrom: purple
colorTo: indigo
sdk: docker
pinned: false
---

# 🎛️ Sound Design RAG

A **retrieval-augmented generation (RAG)** system for audio engineers — mixing engineers, producers, mastering engineers, and singers. Ask technical questions about sound design and get answers grounded in expert reference books.

## 🚀 Quick Start

```bash
# 1. Install dependencies (Python 3.12+)
pip install -r requirements.txt

# 2. Auto-configure API key (reads from Hermes auth)
python setup.py

# 3. Ingest PDFs (already done — chroma_db included in repo)
python ingest.py

# 4. Start the API server
python api.py
```

Then query at **http://localhost:8000/docs** (Swagger UI) or `POST /ask`:

```json
{
  "query": "How do I EQ a vocal to sit better in a mix?",
  "n_results": 5
}
```

## 📚 Knowledge Base

The system is loaded with **1,657 chunks** from 6 expert references:

| Book | Topics |
|---|---|
| **Audio Mixing Cookbook** | EQ, compression, reverb, panning, automation |
| **Mixing Secrets for the Small Studio** | Small-studio workflow, balancing, gain staging |
| **The Mastering Guide** | Loudness, limiting, stereo enhancement, final polish |
| **Fviimusic Tips & Tricks Vol 1-3** | Production tips, creative effects, vocal chains |

Source PDFs live in `data/` (gitignored — not committed to the repo).

## 🧠 Architecture

```
PDFs → extract_text() → chunk_text() → embed (all-MiniLM-L6-v2) → ChromaDB
                                                                    ↓
User Query ──→ query_documents() ──→ build_context() ──→ LLM ──→ Answer
```

- **Embedding**: Local ONNX `all-MiniLM-L6-v2` (free, no API key needed)
- **Vector Store**: ChromaDB (persistent, committed to repo)
- **LLM**: Any OpenAI-compatible provider (DeepSeek, OpenAI, NVIDIA, OpenRouter, etc.)
- **OCR Fallback**: Tesseract for scanned/image-based PDFs

## ⚙️ Configuration

Edit `.env` (gitignored — local only):

```env
# OpenAI-compatible provider (DeepSeek, OpenAI, NVIDIA, etc.)
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

# "local" = built-in ONNX embedding (free)
# "api" = API-based embedding
EMBEDDING_MODE=local

HOST=0.0.0.0
PORT=8000
```

### Auto-Detection

The `setup.py` script automatically detects and writes your API key from Hermes' credential pool (supports Nous OAuth, DeepSeek, NVIDIA, OpenRouter).

### Embedding Modes

| Mode | Description | Cost |
|---|---|---|
| `local` (default) | ChromaDB built-in ONNX `all-MiniLM-L6-v2` | Free |
| `api` | OpenAI-compatible embedding API | API usage |

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | API info |
| `/status` | GET | DB stats, source count, embedding mode |
| `/sources` | GET | List all source documents |
| `/ask` | POST | Ask a sound design question |
| `/docs` | GET | Swagger UI |

### POST /ask

```json
{
  "query": "What's the best compression ratio for vocals?",
  "n_results": 5,
  "source_filter": null,
  "temperature": 0.3
}
```

Response includes the answer, cited sources (book title + page number), and raw context.

## 🛠️ Project Structure

```
sound-design-rag/
├── api.py              # FastAPI server
├── ingest.py           # PDF → chunk → embed → store pipeline
├── query_engine.py     # Search + context building + LLM call
├── config.py           # Settings from .env and env vars
├── setup.py            # Auto-detect API keys from Hermes
├── chroma_db/          # Persistent vector store (committed)
├── data/               # Source PDFs (gitignored)
├── .env.example        # Config template
├── requirements.txt    # Python dependencies
└── .gitignore
```

## 🧪 Testing

```bash
# Command-line query
python query_engine.py "How do I sidechain compress a kick and bass?"

# Run the API
python api.py
# Then: curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"query":"EQ for vocals"}'
```

## 🔄 Re-ingesting PDFs

If you add or update PDFs:

```bash
python ingest.py --force
```

This re-processes all PDFs in `data/` and updates the vector store.
