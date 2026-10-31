"""Embed every corpus chunk with Gemini's text-embedding-004 -> backend/data/vectors.npy. Needs GEMINI_API_KEY in .env.

Run:  .venv/Scripts/python -m backend.ingest.build_index
"""
import sys

import numpy as np

from backend.rag import gemini_client as mc
from backend.rag import store
from backend.rag.store import DATA

if not mc.available():
    sys.exit("GEMINI_API_KEY is not set in .env; the app still works in BM25-only mode.")

chunks = store.corpus()
vecs = mc.embed([f"{c['title']}\n{c['text']}" for c in chunks])
arr = np.array(vecs, dtype=np.float32)
np.save(DATA / "vectors.npy", arr)
print("saved", arr.shape)
