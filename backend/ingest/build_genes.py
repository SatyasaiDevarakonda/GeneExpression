"""Build backend/data/genes.json from the OSCC xlsx plus values read from the in-vitro paper (Fig. 6).

Run:  .venv/Scripts/python backend/ingest/build_genes.py
"""
import json
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
XLSX = ROOT / "data" / "raw" / "OSCC_gene_list.xlsx"
OUT = ROOT / "backend" / "data" / "genes.json"

# Fig. 6 of the in-vitro paper (Natesan et al., Cell Biochem Biophys 2025), values printed on the bars.
# (DTX fold change, DTX significance, MTX fold change, MTX significance); "ns" = not significant.
FIG6 = {
    "BAX": (1.75, "***", 6.73, "****"),
    "CAS3": (1.40, "**", 1.79, "***"),
    "CAS9": (2.23, "***", 1.53, "**"),
    "BCL2": (0.26, "***", 0.35, "****"),
    "BRAF": (0.10, "***", 0.51, "***"),
    "MYC": (0.21, "***", 0.27, "***"),
    "ERBB2": (0.15, "***", 0.15, "**"),
    "SRC": (0.50, "**", 0.45, "*"),
    "TP53": (1.09, "ns", 2.27, "****"),
    "RB1": (1.07, "ns", 1.43, "**"),
    "BRCA1": (1.61, "**", 1.76, "**"),
    "ABCG2": (0.63, "*", 0.49, "**"),
    "SLC7A5": (0.19, "**", 1.21, "*"),
    "SLC10A1": (0.59, "*", 1.80, "***"),
    "CDKN1A": (1.28, "*", 1.11, "ns"),
    "CDK2": (0.38, "**", 0.77, "*"),
    "AURKA": (0.08, "***", 0.93, "ns"),
    "ATM": (1.44, "**", 1.98, "***"),
    "RAD51": (0.31, "**", 0.49, "**"),
    "XPC": (2.03, "****", 2.22, "****"),
    "PARP1": (0.36, "***", 0.62, "**"),
    "MSH2": (2.66, "****", 3.23, "****"),
    "XRCC1": (0.18, "****", 0.32, "***"),
    "VEGFA": (0.29, "**", 0.71, "*"),
    "PDGFB": (0.59, "**", 1.01, "ns"),
    "MAPK1": (0.56, "***", 0.11, "***"),
    "IGIFR": (0.37, "***", 0.47, "**"),
    "PIK3CA": (0.72, "**", 0.66, "**"),
    "PTEN": (0.54, "***", 0.51, "**"),
}
FIG6_CATEGORY = {
    "BAX": "Apoptotic genes", "CAS3": "Apoptotic genes", "CAS9": "Apoptotic genes", "BCL2": "Apoptotic genes",
    "BRAF": "Oncogene", "MYC": "Oncogene", "ERBB2": "Oncogene", "SRC": "Oncogene",
    "TP53": "Tumour suppressor", "RB1": "Tumour suppressor", "BRCA1": "Tumour suppressor",
    "ABCG2": "Drug efflux", "SLC7A5": "Drug uptake transporter", "SLC10A1": "Drug uptake transporter",
    "CDKN1A": "Cell cycle checkpoint", "CDK2": "Cell cycle checkpoint", "AURKA": "Cell cycle checkpoint",
    "ATM": "DNA repair", "RAD51": "DNA repair", "XPC": "DNA repair", "PARP1": "DNA repair",
    "MSH2": "DNA repair", "XRCC1": "DNA repair",
    "VEGFA": "Growth factor", "PDGFB": "Growth factor",
    "MAPK1": "Signal transduction", "IGIFR": "Signal transduction", "PIK3CA": "Signal transduction",
    "PTEN": "Signal transduction",
}

ALIASES = {"IGIFR": "IGF1R", "CAS9": "CASP9", "CAS3": "CASP3"}

# Pathway / process tags, curated from the sheet's category + role text and the pathway names in the review.
PATHWAYS = {
    "PI3K/AKT/mTOR": ["AKT1", "PIK3CA", "PTEN", "GSK3B", "IGIFR", "SLC7A5"],
    "MAPK/RAS-RAF-ERK": ["BRAF", "MAPK1", "MAPK8", "JUN", "SRC", "ERBB2"],
    "Receptor tyrosine kinase": ["ERBB2", "AXL", "IGIFR", "PDGFB", "SRC"],
    "JAK/STAT": ["STAT3", "STAT5B", "IL6"],
    "Wnt/beta-catenin & EMT": ["GSK3B", "AXL", "CXCL12", "SPP1", "CXCL8", "TNF", "SRC", "STAT3", "IL6"],
    "Apoptosis": ["BAX", "BCL2", "CAS3", "CAS9", "TP53", "MAPK8", "CDKN1A"],
    "Cell cycle": ["CDK2", "CDKN1A", "RB1", "AURKA", "MYC", "TP53"],
    "DNA repair & damage response": ["TP53", "ATM", "BRCA1", "PARP1", "MLH1", "MSH2", "XRCC1", "XRCC2",
                                     "ERCC1", "XPC", "RAD51", "CDKN1A"],
    "Drug transport / metabolism": ["ABCG2", "SLC7A5", "SLC10A1", "CYP2E1", "CYP1A1", "GSTM1"],
    "Inflammation & cytokines": ["CXCL8", "CXCL12", "TNF", "IL6", "ANXA1", "CCR5"],
    "ECM remodelling & invasion": ["SPP1", "MMP2", "MMP7", "COL1A2", "CXCL12", "AXL", "TGM3"],
    "Angiogenesis": ["VEGFA", "PDGFB", "CXCL8"],
    "Immune evasion & antigen presentation": ["HLA-C", "CCR5", "IL6", "STAT3"],
    "Transcription factors (AP-1 / MYC / STAT)": ["JUN", "MYC", "STAT3", "STAT5B"],
}

# One coarse group per gene, used for overview charts (curated from the sheet's functional category).
GROUPS = {
    "Signalling & kinases": ["BRAF", "ERBB2", "SRC", "GSK3B", "AKT1", "PIK3CA", "PTEN", "MAPK1", "MAPK8", "AXL",
                             "IGIFR", "STAT3", "STAT5B", "PDGFB"],
    "Transcription factors": ["JUN", "MYC"],
    "Apoptosis": ["BAX", "BCL2", "CAS3", "CAS9"],
    "Cell cycle & tumour suppressors": ["TP53", "CDK2", "CDKN1A", "RB1", "AURKA"],
    "DNA repair": ["BRCA1", "ATM", "PARP1", "MLH1", "XRCC2", "XRCC1", "ERCC1", "XPC", "MSH2", "RAD51"],
    "Drug transport & metabolism": ["ABCG2", "SLC7A5", "SLC10A1", "CYP2E1", "CYP1A1", "GSTM1"],
    "Inflammation & immune": ["CXCL8", "CXCL12", "TNF", "IL6", "ANXA1", "CCR5", "HLA-C"],
    "ECM, invasion & angiogenesis": ["SPP1", "MMP2", "MMP7", "COL1A2", "TGM3", "VEGFA"],
}

# App-curated functional class (NOT from the sheet). Used only for the "biology consistency" lens.
PRO_SURVIVAL = {
    "ABCG2", "SPP1", "CXCL8", "CXCL12", "PDGFB", "SLC7A5", "BRAF", "ERBB2", "SRC", "CDK2", "PARP1", "STAT3",
    "JUN", "AKT1", "MYC", "AURKA", "ERCC1", "TNF", "MMP2", "RAD51", "AXL", "IGIFR", "VEGFA", "PIK3CA", "IL6",
    "COL1A2", "BCL2", "STAT5B", "MMP7", "MAPK1", "CCR5", "GSTM1",
}
PRO_DEATH = {"BAX", "TP53", "CAS9", "CAS3", "CDKN1A", "PTEN", "RB1", "TGM3", "HLA-C", "ATM", "GSK3B"}
# Everything else (DNA-repair genes with ambiguous direction, xenobiotic CYPs, ANXA1, MAPK8, SLC10A1...) = context-dependent.
EXPLORATORY = {"SLC10A1"}


def clean(v):
    return None if v is None else str(v).strip()


def main():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    s1, s2 = wb["OSCC Genes"], wb["Gene status"]

    status = {}
    for row in s2.iter_rows(min_row=2, values_only=True):
        if row[0] and row[1]:
            status[clean(row[0])] = clean(row[1]).lower()

    genes = []
    for row in s1.iter_rows(min_row=2, values_only=True):
        if not isinstance(row[0], (int, float)):
            continue  # skips the trailing "Note:" row
        raw = clean(row[1])
        official = clean(row[2]).split(" (")[0]
        sym = ALIASES.get(raw, official)
        st = status.get(raw)
        drug = []
        if raw in FIG6:
            d_fc, d_sig, m_fc, m_sig = FIG6[raw]
            drug = [
                {"drug": "DTX", "fold_change": d_fc, "significance": d_sig, "direction": "ns" if d_sig == "ns" else ("up" if d_fc > 1 else "down")},
                {"drug": "MTX", "fold_change": m_fc, "significance": m_sig, "direction": "ns" if m_sig == "ns" else ("up" if m_fc > 1 else "down")},
            ]
        cls = "pro-survival" if raw in PRO_SURVIVAL else "pro-death" if raw in PRO_DEATH else "context-dependent"
        sheet_dir = "up" if st == "upregulate" else "down" if st == "downregulate" else None
        if cls == "context-dependent" or sheet_dir is None:
            alignment = "n/a"
        elif (cls == "pro-survival" and sheet_dir == "down") or (cls == "pro-death" and sheet_dir == "up"):
            alignment = "consistent"
        else:
            alignment = "unexpected"

        flags = []
        if raw in ALIASES:
            flags.append(f"Sheet symbol '{raw}' is not an official symbol; interpreted as {ALIASES[raw]}.")
        if raw in EXPLORATORY:
            flags.append("Exploratory: the sheet notes little established OSCC role for this gene.")
        # Sheet vs paper conflicts (both drugs significant and opposite to sheet 2, or either contradicts)
        conflict = None
        if drug and sheet_dir:
            sig_dirs = {x["direction"] for x in drug if x["direction"] != "ns"}
            opposite = "down" if sheet_dir == "up" else "up"
            if sig_dirs == {opposite}:
                conflict = f"Sheet 2 says {sheet_dir}regulated; Fig. 6 shows {opposite}regulation with both DTX and MTX."
            elif opposite in sig_dirs:
                conflict = f"Sheet 2 says {sheet_dir}regulated; Fig. 6 is drug-dependent (opposite for one drug)."
        genes.append({
            "id": int(row[0]),
            "symbol": sym,
            "raw_symbol": raw,
            "full_name": clean(row[3]),
            "category": clean(row[4]),
            "role": clean(row[5]),
            "status_after_chemo": sheet_dir,
            "group": next(gr for gr, members in GROUPS.items() if raw in members),
            "pathways": [p for p, members in PATHWAYS.items() if raw in members],
            "functional_class": cls,
            "biology_alignment": alignment,
            "paper_category": FIG6_CATEGORY.get(raw),
            "drug_data": drug,
            "measured_in_paper": bool(drug),
            "sheet_paper_conflict": conflict,
            "flags": flags,
            "notes": "",
        })

    # ---- integrity checks ----
    assert len(genes) == 54, len(genes)
    missing = [g["raw_symbol"] for g in genes if g["status_after_chemo"] is None]
    assert not missing, f"no status for {missing}"
    assert len(status) == 54, len(status)
    assert set(FIG6) <= {g["raw_symbol"] for g in genes}
    assert len(FIG6) == 29

    OUT.write_text(json.dumps(genes, indent=2, ensure_ascii=False), encoding="utf-8")
    up = sum(g["status_after_chemo"] == "up" for g in genes)
    print(f"{len(genes)} genes: {up} up, {len(genes) - up} down; {len(FIG6)} measured in paper")
    for g in genes:
        if g["sheet_paper_conflict"]:
            print("CONFLICT", g["symbol"], "-", g["sheet_paper_conflict"])
        if g["biology_alignment"] == "unexpected":
            print("UNEXPECTED", g["symbol"], g["functional_class"], g["status_after_chemo"])
    untagged = [g["symbol"] for g in genes if not g["pathways"]]
    print("no pathway:", untagged)


if __name__ == "__main__":
    main()
