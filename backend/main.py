"""OSCC Gene Explorer API.  Run from the repo root:  .venv/Scripts/python -m uvicorn backend.main:app --reload"""
import json
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .rag import chat as chat_mod
from .rag import gemini_client as mc
from .rag import retriever, store
from .rag.store import DATA

app = FastAPI(title="OSCC Gene Explorer")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"genes": len(store.genes()), "chunks": len(store.corpus()), "llm": mc.available(),
            "dense_index": retriever.dense_ready(), "chat_model": mc.CHAT_MODEL if mc.available() else None}


@app.get("/api/genes")
def genes():
    return store.genes()


@app.get("/api/genes/{symbol}")
def gene(symbol: str):
    g = store.find_gene(symbol)
    if not g:
        raise HTTPException(404, f"{symbol} is not in the panel")
    return g


@app.get("/api/overview")
def overview():
    gs = store.genes()
    up = [g for g in gs if g["status_after_chemo"] == "up"]
    groups: dict[str, Counter] = {}
    for g in gs:
        groups.setdefault(g["group"], Counter())[g["status_after_chemo"]] += 1
    lens = Counter(g["biology_alignment"] for g in gs)
    return {
        "total": len(gs), "up": len(up), "down": len(gs) - len(up),
        "measured_in_paper": sum(g["measured_in_paper"] for g in gs),
        "groups": [{"group": k, "up": v["up"], "down": v["down"]} for k, v in groups.items()],
        "alignment": dict(lens),
        "discrepancies": [{"symbol": g["symbol"], "text": g["sheet_paper_conflict"], "sheet": g["status_after_chemo"]}
                          for g in gs if g["sheet_paper_conflict"]],
        "headlines": [
            "Most panel genes (%d of %d) are expected to go DOWN after chemotherapy; %d go up." % (len(gs) - len(up), len(gs), len(up)),
            "Upregulated genes are dominated by pro-apoptotic and tumour-suppressor genes: " + ", ".join(g["symbol"] for g in up) + ".",
            "In KB cells docetaxel (IC50 6.25 nM) was more potent than methotrexate (IC50 100 µM).",
        ],
    }


@app.get("/api/pathways")
def pathways():
    out = []
    for name, gs in store.pathways().items():
        up = [g["symbol"] for g in gs if g["status_after_chemo"] == "up"]
        down = [g["symbol"] for g in gs if g["status_after_chemo"] == "down"]
        out.append({"name": name, "n": len(gs), "up": up, "down": down,
                    "trend": "up" if len(up) > len(down) else "down" if len(down) > len(up) else "mixed"})
    return sorted(out, key=lambda p: -p["n"])


@app.get("/api/network")
def network():
    nodes, edges = [], []
    for g in store.genes():
        nodes.append({"id": g["symbol"], "type": "gene", "status": g["status_after_chemo"], "group": g["group"],
                      "measured": g["measured_in_paper"]})
    for name, gs in store.pathways().items():
        nodes.append({"id": name, "type": "pathway", "n": len(gs)})
        edges += [{"source": g["symbol"], "target": name} for g in gs]
    hubs = json.loads((DATA / "drug_study.json").read_text(encoding="utf-8"))["hub_genes_degree"]
    return {"nodes": nodes, "edges": edges, "hubs": hubs}


@app.get("/api/drug-study")
def drug_study():
    d = json.loads((DATA / "drug_study.json").read_text(encoding="utf-8"))
    d["rtpcr"] = [{"symbol": g["symbol"], "paper_category": g["paper_category"], "sheet_status": g["status_after_chemo"],
                   "drugs": g["drug_data"], "conflict": g["sheet_paper_conflict"]}
                  for g in store.genes() if g["measured_in_paper"]]
    return d


@app.get("/api/literature")
def literature():
    return {
        "table3": json.loads((DATA / "table3.json").read_text(encoding="utf-8")),
        "chunks": [{"id": c["id"], "source": c["source"], "page": c["page"], "text": c["text"], "genes": c["genes"]}
                   for c in store.corpus() if c["source"] in ("In-vitro paper", "Review paper") and c["page"]
                   and not c["title"].startswith("Table 3")],
    }


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[dict] = Field(default=[], max_length=20)
    mode: str = "technical"
    focus_gene: str | None = Field(default=None, max_length=40)


CHAT_LIMIT, CHAT_WINDOW_S = 50, 600
_chat_hits: dict[str, deque] = defaultdict(deque)


def _rate_limited(request: Request) -> bool:
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or request.client.host
    now, q = time.time(), _chat_hits[ip]
    while q and now - q[0] > CHAT_WINDOW_S:
        q.popleft()
    if len(q) >= CHAT_LIMIT:
        return True
    q.append(now)
    return False


@app.post("/api/chat")
def chat(body: ChatIn, request: Request):
    if _rate_limited(request):
        raise HTTPException(429, "Too many questions; please wait a few minutes.")

    def stream():
        for ev in chat_mod.answer(body.message, body.history, body.mode, body.focus_gene):
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if DIST.is_dir():  # production container: serve the built React app from the same origin as the API
    app.mount("/", StaticFiles(directory=DIST, html=True), name="ui")
