"""Hybrid retrieval: BM25 + (optional) dense vectors from Gemini's text-embedding-004, fused with reciprocal rank fusion.
Gene symbols mentioned in the query pin the matching gene cards to the top, so "ERCC1" or "CAS3" always hits."""
import math
import re
from collections import Counter
from functools import lru_cache

import numpy as np

from . import store
from .store import DATA

TOKEN = re.compile(r"[a-z0-9]+")
STOP = set("the of and in to a is are for on with by as at from that this it be or an which what how do does did "
           "gene genes after was were has have can".split())
# prose -> symbol hints so "p53" or "caspase 3" reach the right card
HINTS = {"p53": "tp53", "p21": "cdkn1a", "her2": "erbb2", "vegf": "vegfa", "osteopontin": "spp1", "interleukin": "il6",
         "caspase-3": "casp3", "caspase-9": "casp9", "caspase": "casp3 casp9", "c-myc": "myc", "erk": "mapk1",
         "jnk": "mapk8", "bcl-2": "bcl2", "igf1r": "igifr", "casp3": "cas3", "casp9": "cas9", "cas3": "casp3",
         "cas9": "casp9", "igifr": "igf1r", "docetaxel": "dtx docetaxel", "methotrexate": "mtx methotrexate"}


def tokens(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOP]


class BM25:
    def __init__(self, docs: list[list[str]], k1=1.4, b=0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(d) for d in docs]
        self.len = np.array([len(d) for d in docs], dtype=float)
        self.avg = self.len.mean()
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def scores(self, query: list[str]) -> np.ndarray:
        s = np.zeros(len(self.tf))
        for t in set(query):
            idf = self.idf.get(t)
            if not idf:
                continue
            for i, tf in enumerate(self.tf):
                f = tf.get(t)
                if f:
                    s[i] += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
        return s


@lru_cache(maxsize=1)
def _bm25():
    return BM25([tokens(c["title"] + " " + c["text"]) for c in store.corpus()])


@lru_cache(maxsize=1)
def _vectors():
    p = DATA / "vectors.npy"
    if not p.exists():
        return None
    v = np.load(p)
    if len(v) != len(store.corpus()):
        return None  # stale index: ignore rather than mis-attribute
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def dense_ready() -> bool:
    return _vectors() is not None


def query_symbols(query: str) -> list[str]:
    found = []
    for tok in re.findall(r"[A-Za-z0-9\-]+", query):
        g = store.find_gene(tok)
        if g and g["symbol"] not in found:
            found.append(g["symbol"])
    return found


def search(query: str, k: int = 6, query_vec=None) -> dict:
    """Returns {"hits": [chunk+score], "confidence": "high"|"low", "symbols": [...]}."""
    corpus = store.corpus()
    syms = query_symbols(query)
    q = tokens(query)
    for t in list(q):
        if t in HINTS:
            q += tokens(HINTS[t])

    bm = _bm25().scores(q)
    rankings = [np.argsort(-bm)[:30]]
    vec = _vectors()
    best_dense = None
    if vec is not None and query_vec is not None:
        qv = np.asarray(query_vec, dtype=float)
        sims = vec @ (qv / np.linalg.norm(qv))
        best_dense = float(sims.max())
        rankings.append(np.argsort(-sims)[:30])

    fused: dict[int, float] = {}
    for r in rankings:
        for rank, i in enumerate(r):
            fused[int(i)] = fused.get(int(i), 0.0) + 1.0 / (60 + rank)
    # pin gene cards for symbols named in the query
    for i, c in enumerate(corpus):
        if c["source"] == "Gene card" and c["title"] in syms:
            fused[i] = fused.get(i, 0.0) + 1.0
    # measured genes: pin the Fig. 6 table, and the sheet-vs-paper check when that gene is in conflict
    for i, c in enumerate(corpus):
        if c["title"].startswith("Fig. 6") and any(store.find_gene(s)["measured_in_paper"] for s in syms):
            fused[i] = fused.get(i, 0.0) + 0.5
        if c["source"] == "Data check" and any(store.find_gene(s)["sheet_paper_conflict"] for s in syms):
            fused[i] = fused.get(i, 0.0) + 0.5
    # other chunks that mention a queried symbol get a smaller boost
    for i, c in enumerate(corpus):
        if syms and set(syms) & set(c["genes"]):
            fused[i] = fused.get(i, 0.0) + 0.01

    order = sorted(fused, key=fused.get, reverse=True)[:k]
    hits = [{**corpus[i], "score": round(fused[i], 4)} for i in order]

    top_bm = float(bm.max()) if len(bm) else 0.0
    confident = bool(syms) or top_bm >= 6.0 or (best_dense is not None and best_dense >= 0.62)
    return {"hits": hits, "confidence": "high" if confident else "low", "symbols": syms}
