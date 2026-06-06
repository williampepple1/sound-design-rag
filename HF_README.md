---
title: Sound Design RAG
emoji: 🎛️
colorFrom: purple
colorTo: indigo
sdk: docker
pinned: false
---

# Sound Design RAG

A retrieval-augmented generation system for audio engineers. Ask questions about mixing, mastering, production, and vocals — answers are grounded in expert reference books.

## Usage

Ask anything about sound design. Examples:

- "How do I EQ a vocal to sit better in a mix?"
- "What compression settings work best for drums?"
- "How do I prepare a mix for mastering?"
- "What's the best way to use reverb on vocals?"

## Environment Variables (Secrets)

Set these in the Space Settings → Repository Secrets:

| Secret | Description |
|---|---|
| `LLM_API_KEY` | Your OpenAI-compatible API key (DeepSeek, OpenAI, etc.) |
| `LLM_BASE_URL` | API base URL (e.g. `https://api.deepseek.com`) |
| `LLM_MODEL` | Model name (e.g. `deepseek-chat`) |

> **Note:** Embedding mode is `local` (built-in ONNX `all-MiniLM-L6-v2`) — no API key needed for embeddings.
