#!/usr/bin/env python3
"""Check deps for the global python."""
import importlib, sys

pkgs = [
    "pymupdf",
    "numpy",
    "openai",
    "fastapi",
    "uvicorn",
    "chromadb",
    "sentence_transformers",
]

for name in pkgs:
    try:
        m = importlib.import_module(name)
        v = getattr(m, "__version__", "ok")
        print(f"  {name}: {v}")
    except ImportError:
        print(f"  {name}: MISSING")

print(f"\nPython: {sys.version}")
print(f"Executable: {sys.executable}")
