#!/usr/bin/env python
"""Check available Python dependencies for the RAG project."""
import sys, subprocess

pkgs = {
    "pymupdf": "PyMuPDF",
    "chromadb": "chromadb",
    "sentence_transformers": "sentence-transformers",
    "fastapi": "fastapi",
    "openai": "openai",
    "uvicorn": "uvicorn",
    "numpy": "numpy",
}

for import_name, pip_name in pkgs.items():
    try:
        mod = __import__(import_name)
        ver = getattr(mod, "__version__", "OK")
        print(f"  {import_name} ({pip_name}): {ver}")
    except ImportError:
        print(f"  {import_name} ({pip_name}): MISSING")
    except Exception as e:
        print(f"  {import_name} ({pip_name}): ERROR {e}")

print(f"\nPython: {sys.version}")
print(f"Executable: {sys.executable}")
