"""
Sound Design RAG - Query Engine.

Retrieves relevant chunks from ChromaDB, builds context,
and queries the LLM for sound design answers.
"""
from typing import List, Dict, Optional

import chromadb
from openai import OpenAI

import config


# System prompt tailored for sound design professionals
SYSTEM_PROMPT = """You are a world-class sound design and audio engineering assistant.
You help mixing engineers, producers, mastering engineers, and singers.

Your knowledge comes from expert reference books. Always cite your sources
by mentioning the book title and page number where relevant.

Be specific, practical, and technical. Include concrete numbers, frequencies,
dB ranges, and techniques — not vague generalities.

**Roles you support:**
- **Mixing Engineers**: EQ, compression, reverb, panning, automation, gain staging, balancing
- **Producers**: Arrangement, sound selection, creative effects, production workflow
- **Mastering Engineers**: Loudness, limiting, stereo enhancement, final polish, format specs
- **Singers/Vocalists**: Vocal chain, recording technique, doubling, tuning, de-essing

When asked about a topic you don't have context for, say so honestly.
Do not invent citations or page numbers."""


def get_client() -> chromadb.PersistentClient:
    """Get the persistent ChromaDB client."""
    return chromadb.PersistentClient(path=str(config.CHROMA_DB_DIR))


def get_collection(client: chromadb.PersistentClient):
    """Get the sound design collection."""
    return client.get_collection("sound_design_docs")


def get_llm_client() -> OpenAI:
    """Get the OpenAI-compatible LLM client."""
    return OpenAI(
        api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
    )


def query_documents(
    query: str,
    n_results: int = 5,
    source_filter: Optional[str] = None,
) -> List[Dict]:
    """
    Search the vector database for relevant chunks.

    Args:
        query: The user's question.
        n_results: Number of chunks to retrieve.
        source_filter: Optional source file name to filter by.

    Returns:
        List of dicts with text, source_file, page_num, and distance.
    """
    client = get_client()
    collection = get_collection(client)

    where_filter = None
    if source_filter:
        where_filter = {"source_file": source_filter}

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where_filter,
    )

    chunks = []
    if results and results["documents"] and results["documents"][0]:
        for i in range(len(results["documents"][0])):
            chunks.append({
                "text": results["documents"][0][i],
                "source_file": results["metadatas"][0][i]["source_file"],
                "page_num": results["metadatas"][0][i]["page_num"],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })

    return chunks


def build_context(chunks: List[Dict]) -> str:
    """
    Build a formatted context string from retrieved chunks.
    """
    context_parts = []
    seen_sources = set()

    for i, chunk in enumerate(chunks, 1):
        source_info = f"[Source: {chunk['source_file']}, Page {chunk['page_num']}]"
        context_parts.append(f"--- Excerpt {i} {source_info} ---\n{chunk['text']}\n")
        seen_sources.add(chunk['source_file'])

    return "\n".join(context_parts)


def ask(
    query: str,
    n_results: int = 5,
    source_filter: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.3,
) -> Dict:
    """
    Full RAG query: retrieve relevant chunks, build context, ask LLM.

    Args:
        query: User's question.
        n_results: Number of chunks to retrieve.
        source_filter: Optional source filter.
        model: Override the LLM model.
        temperature: LLM temperature (0.0-1.0).

    Returns:
        Dict with 'answer' (str), 'sources' (list of dicts), and 'context' (str).
    """
    # 1. Retrieve relevant documents
    chunks = query_documents(
        query=query,
        n_results=n_results,
        source_filter=source_filter,
    )

    if not chunks:
        return {
            "answer": "I couldn't find relevant information in the knowledge base "
                      "to answer your question. Please try rephrasing or ask about "
                      "a different sound design topic.",
            "sources": [],
            "context": "",
        }

    # 2. Build context
    context = build_context(chunks)

    # 3. Build LLM prompt
    user_prompt = f"""Use the following reference material to answer the question.
Base your answer ONLY on the provided excerpts.

CONTEXT:
{context}

QUESTION: {query}

Answer thoroughly and technically. Include specific numbers, frequencies, and techniques
when present in the context. Cite the source book and page number for key claims."""

    # 4. Call LLM
    llm = get_llm_client()
    response = llm.chat.completions.create(
        model=model or config.LLM_MODEL,
        temperature=temperature,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    answer = response.choices[0].message.content

    # 5. Extract unique sources
    sources = []
    seen = set()
    for c in chunks:
        key = (c["source_file"], c["page_num"])
        if key not in seen:
            seen.add(key)
            sources.append({
                "source_file": c["source_file"],
                "page_num": c["page_num"],
            })

    return {
        "answer": answer,
        "sources": sources,
        "context": context,
    }


def list_sources() -> List[str]:
    """List all unique source files in the database."""
    client = get_client()
    collection = get_collection(client)
    results = collection.get()
    sources = set()
    if results and results.get("metadatas"):
        for m in results["metadatas"]:
            sources.add(m["source_file"])
    return sorted(sources)


def count_documents() -> int:
    """Get the total document count in the vector DB."""
    client = get_client()
    collection = get_collection(client)
    return collection.count()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python query_engine.py \"your question\"")
        print(f"   DB has {count_documents()} documents")
        print(f"   Sources: {list_sources()}")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    result = ask(query)
    print(f"\n{'='*60}")
    print(f"Q: {query}")
    print(f"{'='*60}\n")
    print(result["answer"])
    print(f"\n{'='*60}")
    print("Sources:")
    for s in result["sources"]:
        print(f"  • {s['source_file']} (p. {s['page_num']})")
