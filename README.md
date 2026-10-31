# OSCC Gene Explorer

Dashboard + cited RAG chatbot for the 54-gene OSCC panel (post-chemotherapy status), the in-vitro DTX/MTX paper and the HNSCC review.

## Setup (Windows, from this folder)
```
python -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements.txt
cd frontend && npm install && cd ..
copy .env.example .env        # then put your GEMINI_API_KEY in .env
```

## Build the data (already generated; re-run if the xlsx/PDFs change)
```
.venv\Scripts\python backend\ingest\build_genes.py
.venv\Scripts\python backend\ingest\build_corpus.py
.venv\Scripts\python -m backend.ingest.build_index     # needs the API key; adds semantic search
```

## Run
```
.venv\Scripts\python -m uvicorn backend.main:app --port 8000     # terminal 1
cd frontend && npm run dev                                       # terminal 2 -> http://localhost:5173
```

## Test
```
.venv\Scripts\python -m pytest tests -q
```

## Deploy
Vercel (free): `vercel.json` builds the React app as static files and runs the FastAPI backend from `api/index.py` as a Python function (runtime deps in the root `requirements.txt`). Set `GEMINI_API_KEY` in the Vercel project's Environment Variables.

## How it works
- `data/raw/`: the original xlsx and PDFs, kept locally and not committed; only needed to rebuild `backend/data/`.
- `backend/ingest/`: builds `genes.json` (sheet + Fig. 6 values), `corpus.jsonl` (gene cards, paper passages, review Table 3) and the embedding index.
- `backend/rag/`: hybrid retrieval (BM25 + Gemini embeddings, rank-fused, gene symbols pinned), structured tools for counts/filters, guardrails, streamed answers with `[citation]` labels.
- `frontend/`: React dashboard (Overview, Gene table, Expression response, Pathways, Network, Drug study, Literature, Chatbot, About).

## Data caveats (also shown in the app)
- Fig. 6 fold changes were read from bar labels in the figure; confirm against your raw data.
- Sheet 2 conflicts with Fig. 6 for BRCA1, XPC, MSH2, PTEN (both drugs) and SLC7A5, SLC10A1 (drug-dependent).
- Pathway tags, gene groups and the pro-survival/pro-death class are app-curated for navigation, not from the papers.
- Research use only; not medical advice.
