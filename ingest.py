"""
Sound Design RAG - PDF Ingestion Pipeline.

Extracts text from PDFs, chunks them, embeds, and stores in ChromaDB.
"""
import os
import re
import hashlib
from pathlib import Path
from typing import List, Optional

import pymupdf  # PyMuPDF
import chromadb
from chromadb.utils import embedding_functions as ef

import config


def extract_text_from_pdf(pdf_path: Path) -> List[dict]:
    """
    Extract text from a PDF file page by page.
    Uses OCR fallback for image-based/scanned PDFs.
    Returns list of dicts: {page_num, text, source_file}.
    """
    pages = []
    doc = pymupdf.open(str(pdf_path))
    source = pdf_path.name

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        # If no text extracted, try OCR (for scanned/image-based PDFs)
        if len(text.strip()) < 20:
            try:
                tp = page.get_textpage_ocr(
                    flags=0, language='eng', dpi=200, full=True
                )
                text = tp.extractText()
            except Exception:
                pass  # OCR failed, keep what we have

        # Skip nearly-empty pages
        if len(text.strip()) < 20:
            continue

        pages.append({
            "page_num": page_num + 1,
            "text": text,
            "source_file": source,
        })

    doc.close()
    return pages


def chunk_text(pages: List[dict],
               chunk_size: int = 1000,
               chunk_overlap: int = 200) -> List[dict]:
    """
    Split extracted pages into overlapping chunks of roughly `chunk_size` chars.
    Each chunk preserves its source and page number.

    Uses a simple sliding-window approach that respects paragraph breaks.
    """
    chunks = []

    for page in pages:
        text = page["text"]
        source = page["source_file"]
        page_num = page["page_num"]

        # Split into paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)
        current_chunk = ""
        current_paragraphs = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph exceeds chunk size, save current chunk
            if len(current_chunk) + len(para) + 1 > chunk_size and current_chunk:
                chunk_id = hashlib.md5(
                    f"{source}|p{page_num}|{len(chunks)}|{current_chunk[:50]}".encode()
                ).hexdigest()[:12]

                chunks.append({
                    "id": chunk_id,
                    "text": current_chunk.strip(),
                    "source_file": source,
                    "page_num": page_num,
                    "chunk_index": len(chunks),
                })

                # Keep overlap: last few paragraphs for context
                overlap_text = ""
                for p in current_paragraphs[-3:]:
                    if len(overlap_text) + len(p) + 1 < chunk_overlap:
                        overlap_text += p + "\n\n"
                current_chunk = overlap_text.strip()
                current_paragraphs = current_paragraphs[-3:]

            current_chunk += para + "\n\n"
            current_paragraphs.append(para)

        # Don't forget the last chunk
        if current_chunk.strip():
            chunk_id = hashlib.md5(
                f"{source}|p{page_num}|{len(chunks)}|{current_chunk[:50]}".encode()
            ).hexdigest()[:12]
            chunks.append({
                "id": chunk_id,
                "text": current_chunk.strip(),
                "source_file": source,
                "page_num": page_num,
                "chunk_index": len(chunks),
            })

    return chunks


def get_embedding_function():
    """Get the appropriate embedding function based on config."""
    if config.EMBEDDING_MODE == "api":
        return ef.OpenAIEmbeddingFunction(
            api_key=config.EMBEDDING_API_KEY,
            api_base=config.EMBEDDING_BASE_URL,
            model_name=config.EMBEDDING_MODEL,
        )
    else:
        # Local: ChromaDB built-in ONNX all-MiniLM-L6-v2
        return ef.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )


def get_or_create_collection(client):
    """Get existing collection or create a new one."""
    collection_name = "sound_design_docs"

    try:
        collection = client.get_collection(collection_name)
        print(f"  Found existing collection '{collection_name}' "
              f"({collection.count()} documents)")
        return collection
    except Exception:
        pass

    embed_fn = get_embedding_function()
    collection = client.create_collection(
        name=collection_name,
        embedding_function=embed_fn,
        metadata={"description": "Sound design RAG - mixing, mastering, production"}
    )
    print(f"  Created collection '{collection_name}'")
    return collection


def hash_file(path: Path) -> str:
    """SHA-256 hash of file contents for change detection."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_processed_files(client) -> set:
    """Load set of already-processed file hashes from ChromaDB metadata."""
    collection = None
    try:
        collection = client.get_collection("sound_design_docs")
    except Exception:
        return set()

    try:
        meta_collection = client.get_collection("ingestion-meta")
    except Exception:
        meta_collection = client.create_collection(
            "ingestion-meta",
            embedding_function=ef.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            ),
        )

    results = meta_collection.get()
    if results and results.get("ids"):
        # The IDs ARE the file hashes
        return set(results["ids"])
    return set()


def save_processed_file(client, file_hash: str, filename: str):
    """Record a processed file hash in ChromaDB metadata."""
    try:
        meta_collection = client.get_collection("ingestion-meta")
    except Exception:
        meta_collection = client.create_collection(
            "ingestion-meta",
            embedding_function=ef.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            ),
        )

    # Use empty embedding since this collection is metadata-only
    meta_collection.add(
        ids=[file_hash],
        metadatas=[{"filename": filename, "processed_at": str(__import__('datetime').datetime.now())}],
        documents=["processed"],
    )


def run_ingest(pdf_dir: Optional[Path] = None, force: bool = False):
    """
    Main ingestion pipeline: extract → chunk → embed → store.

    Args:
        pdf_dir: Directory containing PDF files. Defaults to config.PDF_DIR.
        force: If True, re-process all PDFs even if already ingested.
    """
    if pdf_dir is None:
        pdf_dir = config.PDF_DIR

    pdf_dir = Path(pdf_dir)
    if not pdf_dir.exists():
        print(f"ERROR: PDF directory not found: {pdf_dir}")
        print("Copy your PDFs there and re-run.")
        return

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return

    print(f"Found {len(pdf_files)} PDF(s) to process\n")

    # Connect to ChromaDB (persistent)
    client = chromadb.PersistentClient(path=str(config.CHROMA_DB_DIR))
    collection = get_or_create_collection(client)
    processed = load_processed_files(client)

    total_chunks_added = 0
    total_chunks_skipped = 0

    for pdf_path in pdf_files:
        print(f"📄 {pdf_path.name}...")

        # Check if already processed
        file_hash = hash_file(pdf_path)

        if file_hash in processed and not force:
            print(f"   → Already ingested (use --force to re-process)")
            total_chunks_skipped += collection.count()
            continue

        # Extract text
        pages = extract_text_from_pdf(pdf_path)
        print(f"   Extracted {len(pages)} pages")

        # Chunk text
        chunks = chunk_text(
            pages,
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
        )
        print(f"   Created {len(chunks)} chunks")

        # Prepare for ChromaDB
        ids = [c["id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [
            {
                "source_file": c["source_file"],
                "page_num": c["page_num"],
                "chunk_index": c["chunk_index"],
            }
            for c in chunks
        ]

        # Add to ChromaDB (batch add to avoid memory issues)
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            end = min(i + batch_size, len(chunks))
            collection.add(
                ids=ids[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end],
            )

        # Mark as processed
        save_processed_file(client, file_hash, pdf_path.name)

        total_chunks_added += len(chunks)
        print(f"   ✓ Stored {len(chunks)} chunks in vector DB")

    total = collection.count()
    print(f"\n{'='*50}")
    print(f"✅ Ingestion complete!")
    print(f"   Total documents in vector DB: {total}")
    print(f"   Chunks added this run: {total_chunks_added}")
    print(f"   Collection: sound_design_docs")
    print(f"   DB location: {config.CHROMA_DB_DIR}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest PDFs into the RAG vector DB")
    parser.add_argument("--pdf-dir", type=str, default=None,
                        help="Directory with PDF files")
    parser.add_argument("--force", action="store_true",
                        help="Re-process all PDFs even if already ingested")
    args = parser.parse_args()

    run_ingest(
        pdf_dir=Path(args.pdf_dir) if args.pdf_dir else None,
        force=args.force,
    )
