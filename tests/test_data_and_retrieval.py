"""Data-integrity and retrieval checks. Run from repo root:  .venv/Scripts/python -m pytest tests -q
Needs no API key (BM25 path). Rebuild data first: backend/ingest/build_genes.py then build_corpus.py."""
import openpyxl
import pytest

from backend.rag import chat, retriever, store, tools

XLSX = "data/raw/OSCC_gene_list.xlsx"


def test_gene_count_and_status_match_sheet2():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    sheet2 = {r[0].strip(): r[1].strip().lower() for r in wb["Gene status"].iter_rows(min_row=2, values_only=True) if r[0] and r[1]}
    genes = store.genes()
    assert len(genes) == 54 and len(sheet2) == 54
    for g in genes:
        expect = "up" if sheet2[g["raw_symbol"]] == "upregulate" else "down"
        assert g["status_after_chemo"] == expect, g["symbol"]
    assert sum(g["status_after_chemo"] == "up" for g in genes) == 12


def test_aliases_resolve():
    for alias, official in [("IGIFR", "IGF1R"), ("CAS9", "CASP9"), ("CAS3", "CASP3"), ("igf1r", "IGF1R")]:
        assert store.find_gene(alias)["symbol"] == official


def test_every_gene_has_card_pathway_and_group():
    cards = {c["title"] for c in store.corpus() if c["source"] == "Gene card"}
    for g in store.genes():
        assert g["symbol"] in cards and g["pathways"] and g["group"]


def test_fig6_values_spot_check():
    g = store.find_gene("BAX")
    assert [d["fold_change"] for d in g["drug_data"]] == [1.75, 6.73]
    assert store.find_gene("PTEN")["sheet_paper_conflict"]
    assert not store.find_gene("BAX")["sheet_paper_conflict"]
    assert sum(g["measured_in_paper"] for g in store.genes()) == 29


# (query, citation that must appear in top 3 hits)
GOLD = [
    ("What does ERCC1 do?", "Sheet: ERCC1"),
    ("CAS3 status after chemo", "Sheet: CASP3"),
    ("IGIFR expression", "Sheet: IGF1R"),
    ("TP53 mutation frequency in OSCC", "Sheet: TP53"),
    ("BRCA1 fold change docetaxel", "In-vitro paper Fig. 6"),
    ("docetaxel IC50 value", "In-vitro paper p.1"),
    ("which genes differ between sheet and paper", "Data check: sheet vs paper"),
    ("ABCB1 upregulated cisplatin resistance", "Review paper Table 3"),
    ("GSTM1 glutathione resistance", "Sheet: GSTM1"),
    ("osteopontin invasion", "Sheet: SPP1"),
]


@pytest.mark.parametrize("query,expected", GOLD)
def test_gold_retrieval(query, expected):
    cites = [h["citation"] for h in retriever.search(query, k=6)["hits"][:3]]
    assert expected in cites, cites


@pytest.mark.parametrize("query", ["best pizza recipe in Rome", "who won the football world cup"])
def test_out_of_scope_is_low_confidence(query):
    assert retriever.search(query)["confidence"] == "low"


def test_tools_counts_are_exact():
    assert tools.run("list_genes", {"status": "up"})["count"] == 12
    assert tools.run("list_genes", {"discrepancy_only": True})["count"] == 6
    assert tools.run("get_gene", {"symbol": "nope"})["error"]
    assert "Apoptosis" in tools.run("pathway_summary", {"name": "apopt"})["pathways"]


def test_medical_advice_is_refused_without_calling_model():
    out = "".join(e.get("text", "") for e in chat.answer("Which drug should I take for my cancer?"))
    assert "can't give" in out


def test_retrieval_only_mode_refuses_offtopic(monkeypatch):
    monkeypatch.setattr("backend.rag.gemini_client.available", lambda: False)
    out = "".join(e.get("text", "") for e in chat.answer("best pizza recipe in Rome"))
    assert "not in the provided data" in out


def test_llm_path_tool_loop_and_streaming_with_fake_model(monkeypatch):
    """Exercises tool-call -> tool result -> streamed answer without a real API key."""
    seen = {}

    def fake_chat(msgs, tools=None, **kw):
        if not any(m["role"] == "tool" for m in msgs):
            return {"content": "", "tool_calls": [{"id": "t1", "function": {"name": "list_genes", "arguments": '{"status": "up"}'}}]}
        seen["tool_content"] = [m["content"] for m in msgs if m["role"] == "tool"][0]
        return {"content": None}  # model replies after tools; stream path takes over

    monkeypatch.setattr("backend.rag.gemini_client.available", lambda: True)
    monkeypatch.setattr("backend.rag.gemini_client.chat", fake_chat)
    monkeypatch.setattr("backend.rag.gemini_client.chat_stream", lambda msgs, **kw: iter(["12 genes ", "[Sheet 2: gene status]"]))
    monkeypatch.setattr("backend.rag.retriever.dense_ready", lambda: False)
    events = list(chat.answer("how many genes go up?"))
    text = "".join(e.get("text", "") for e in events if e["type"] == "token")
    assert '"count": 12' in seen["tool_content"]
    assert "12 genes" in text and events[-1]["type"] == "done"
    assert any(e["type"] == "sources" and e.get("append") for e in events)  # tool genes offered as citable cards


def test_llm_failure_degrades_to_retrieval(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr("backend.rag.gemini_client.available", lambda: True)
    monkeypatch.setattr("backend.rag.gemini_client.chat", boom)
    events = list(chat.answer("What does ERCC1 do?"))
    assert any(e["type"] == "error" for e in events)
    assert "ERCC1" in "".join(e.get("text", "") for e in events if e["type"] == "token")
