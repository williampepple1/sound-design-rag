"""
Sound Design RAG - FastAPI Server.

Provides REST API endpoints for querying the RAG system.
"""
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from query_engine import ask, list_sources, count_documents

app = FastAPI(
    title="Sound Design RAG API",
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
    """API root with status."""
    return {
        "name": "Sound Design RAG API",
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

    print(f"Starting Sound Design RAG API on http://{config.HOST}:{config.PORT}")
    print(f"Embedding mode: {config.EMBEDDING_MODE}")
    print(f"LLM model: {config.LLM_MODEL}")
    print(f"API docs: http://{config.HOST}:{config.PORT}/docs")

    uvicorn.run(
        "api:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
    )
