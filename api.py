"""
Sound Design RAG - FastAPI Server.

Provides REST API endpoints for querying the RAG system.
"""
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

import config
from query_engine import ask, list_sources, count_documents

app = FastAPI(
    title="Sound Design RAG",
    description="RAG-powered sound design assistant for mixing engineers, "
                "producers, mastering engineers, and singers.",
    version="1.0.0",
)

# Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- Request/Response Models ---

class QueryRequest(BaseModel):
    query: str
    n_results: int = 5
    source_filter: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.3


class QueryResponse(BaseModel):
    answer: str
    sources: list
    context: Optional[str] = None


class StatusResponse(BaseModel):
    status: str
    documents: int
    sources: list
    embedding_mode: str


# --- Endpoints ---

@app.get("/", tags=["Info"])
async def root():
    """Serve the chat UI."""
    index = STATIC_DIR / "index.html"
    if STATIC_DIR.exists() and index.exists():
        return FileResponse(str(index))
    return {
        "name": "Sound Design RAG",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/status", response_model=StatusResponse, tags=["Info"])
async def get_status():
    """Get the RAG system status: document count, available sources, etc."""
    try:
        doc_count = count_documents()
        srcs = list_sources()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {str(e)}. Run `python ingest.py` first."
        )

    return StatusResponse(
        status="ready" if doc_count > 0 else "empty",
        documents=doc_count,
        sources=srcs,
        embedding_mode=config.EMBEDDING_MODE,
    )


@app.post("/ask", response_model=QueryResponse, tags=["Query"])
async def ask_question(req: QueryRequest):
    """
    Ask a question about sound design.

    The system retrieves relevant passages from the knowledge base
    and generates an answer using the configured LLM.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        result = ask(
            query=req.query,
            n_results=req.n_results,
            source_filter=req.source_filter,
            model=req.model,
            temperature=req.temperature,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}. Ensure LLM_API_KEY is set in .env"
        )

    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        context=result.get("context"),
    )


@app.get("/sources", tags=["Info"])
async def get_sources():
    """List all source documents in the knowledge base."""
    return {"sources": list_sources()}


# --- Run ---
if __name__ == "__main__":
    import uvicorn

    port = config.PORT
    print(f"🎛️  Sound Design RAG")
    print(f"   UI:      http://{config.HOST}:{port}")
    print(f"   API:     http://{config.HOST}:{port}/ask")
    print(f"   Docs:    http://{config.HOST}:{port}/docs")
    print(f"   DB:      {count_documents()} documents")
    print(f"   LLM:     {config.LLM_MODEL}")
    print(f"   Embed:   {config.EMBEDDING_MODE}")

    uvicorn.run(
        "api:app",
        host=config.HOST,
        port=port,
    )
