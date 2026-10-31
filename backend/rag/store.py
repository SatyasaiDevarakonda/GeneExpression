"""Loads the generated data files once and exposes lookups shared by the API, tools and retriever."""
import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


@lru_cache(maxsize=1)
def genes() -> list[dict]:
    return json.loads((DATA / "genes.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def corpus() -> list[dict]:
    return [json.loads(line) for line in (DATA / "corpus.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


@lru_cache(maxsize=1)
def gene_index() -> dict[str, dict]:
    """Case-insensitive lookup by official symbol, raw sheet symbol, and the IGF1R/CASP aliases."""
    idx = {}
    for g in genes():
        idx[g["symbol"].upper()] = g
        idx[g["raw_symbol"].upper()] = g
    return idx


def find_gene(symbol: str) -> dict | None:
    return gene_index().get(symbol.strip().upper().replace("_", "-"))


def pathways() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for g in genes():
        for p in g["pathways"]:
            out.setdefault(p, []).append(g)
    return out
