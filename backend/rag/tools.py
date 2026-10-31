"""Structured tools the LLM can call so counts/filters/comparisons come from the data, not from memory."""
from . import store

STATUS_WORD = {"up": "upregulated", "down": "downregulated"}


def _brief(g: dict) -> dict:
    return {
        "symbol": g["symbol"], "sheet_symbol": g["raw_symbol"], "full_name": g["full_name"],
        "category": g["category"], "status_after_chemo_sheet2": STATUS_WORD[g["status_after_chemo"]],
        "pathways": g["pathways"], "measured_in_paper": g["measured_in_paper"],
        "cite_as": f"[Sheet: {g['symbol']}]",
    }


def _full(g: dict) -> dict:
    d = _brief(g)
    d["role_in_OSCC_sheet1"] = g["role"]
    d["functional_class_app_curated"] = g["functional_class"]
    if g["drug_data"]:
        d["fig6_rtpcr_fold_change"] = {x["drug"]: f"{x['fold_change']} ({x['significance']})" for x in g["drug_data"]}
        d["fig6_cite_as"] = "[In-vitro paper Fig. 6]"
    if g["sheet_paper_conflict"]:
        d["discrepancy"] = g["sheet_paper_conflict"]
    if g["flags"]:
        d["flags"] = g["flags"]
    return d


def get_gene(symbol: str):
    g = store.find_gene(symbol)
    return _full(g) if g else {"error": f"'{symbol}' is not in the 54-gene panel"}


def list_genes(status: str | None = None, category_contains: str | None = None, pathway_contains: str | None = None,
               functional_class: str | None = None, measured_in_paper: bool | None = None,
               fig6_direction: str | None = None, discrepancy_only: bool = False):
    out = []
    for g in store.genes():
        if status and g["status_after_chemo"] != ("up" if status.lower().startswith("up") else "down"):
            continue
        if category_contains and category_contains.lower() not in g["category"].lower():
            continue
        if pathway_contains and not any(pathway_contains.lower() in p.lower() for p in g["pathways"]):
            continue
        if functional_class and g["functional_class"] != functional_class:
            continue
        if measured_in_paper is not None and g["measured_in_paper"] != measured_in_paper:
            continue
        if fig6_direction and not any(x["direction"] == fig6_direction for x in g["drug_data"]):
            continue
        if discrepancy_only and not g["sheet_paper_conflict"]:
            continue
        out.append(g)
    return {"count": len(out), "genes": [{"symbol": g["symbol"], "status": STATUS_WORD[g["status_after_chemo"]],
                                          "category": g["category"]} for g in out],
            "cite_as": "[Sheet 2: gene status]"}


def compare_genes(symbols: list[str]):
    res = []
    for s in symbols[:6]:
        g = store.find_gene(s)
        res.append(_full(g) if g else {"error": f"'{s}' is not in the panel"})
    return {"genes": res}


def pathway_summary(name: str):
    matches = {p: gs for p, gs in store.pathways().items() if name.lower() in p.lower()}
    if not matches:
        return {"error": f"No pathway matching '{name}'", "available": list(store.pathways())}
    out = {}
    for p, gs in matches.items():
        out[p] = {
            "n_genes": len(gs),
            "upregulated": [g["symbol"] for g in gs if g["status_after_chemo"] == "up"],
            "downregulated": [g["symbol"] for g in gs if g["status_after_chemo"] == "down"],
        }
    return {"pathways": out, "cite_as": "[Sheet 2: gene status]"}


def study_overview():
    gs = store.genes()
    up = [g["symbol"] for g in gs if g["status_after_chemo"] == "up"]
    return {
        "total_genes": len(gs), "upregulated_count": len(up), "downregulated_count": len(gs) - len(up),
        "upregulated": up, "measured_by_rtpcr_in_paper": sum(g["measured_in_paper"] for g in gs),
        "discrepancies_sheet_vs_paper": [g["symbol"] for g in gs if g["sheet_paper_conflict"]],
        "pathways": list(store.pathways()),
        "cite_as": "[Sheet 2: gene status]",
    }


FUNCS = {
    "get_gene": get_gene, "list_genes": list_genes, "compare_genes": compare_genes,
    "pathway_summary": pathway_summary, "study_overview": study_overview,
}

SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_gene", "description": "Full record for one gene of the 54-gene panel (accepts aliases like CAS3, IGF1R).",
        "parameters": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}}},
    {"type": "function", "function": {
        "name": "list_genes",
        "description": "Filter the panel. Use for any question about counts or 'which genes ...'. All filters optional and combined with AND.",
        "parameters": {"type": "object", "properties": {
            "status": {"type": "string", "enum": ["up", "down"], "description": "Sheet 2 status after chemotherapy"},
            "category_contains": {"type": "string", "description": "Substring of the functional category, e.g. 'DNA repair'"},
            "pathway_contains": {"type": "string", "description": "Substring of a pathway name, e.g. 'PI3K', 'Apoptosis'"},
            "functional_class": {"type": "string", "enum": ["pro-survival", "pro-death", "context-dependent"]},
            "measured_in_paper": {"type": "boolean"},
            "fig6_direction": {"type": "string", "enum": ["up", "down"], "description": "Direction seen with either drug in Fig. 6"},
            "discrepancy_only": {"type": "boolean", "description": "Only genes where sheet 2 conflicts with the paper"}}}}},
    {"type": "function", "function": {
        "name": "compare_genes", "description": "Side-by-side records for up to 6 genes.",
        "parameters": {"type": "object", "properties": {"symbols": {"type": "array", "items": {"type": "string"}}},
                       "required": ["symbols"]}}},
    {"type": "function", "function": {
        "name": "pathway_summary", "description": "Genes in a pathway/process split into up- and downregulated.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "study_overview", "description": "Panel-level counts and the list of sheet-vs-paper discrepancies.",
        "parameters": {"type": "object", "properties": {}}}},
]


def run(name: str, args: dict):
    fn = FUNCS.get(name)
    if not fn:
        return {"error": f"unknown tool {name}"}
    try:
        return fn(**args)
    except TypeError as e:
        return {"error": f"bad arguments: {e}"}
