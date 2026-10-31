"""Build backend/data/corpus.jsonl: the citable chunks the chatbot retrieves from.

Chunk sources (tier = how much weight the claim deserves):
  A  the team's own study: sheet 2 status + the in-vitro paper
  B  the review paper
  C  sheet 1 background text (literature summaries; the sheet asks for verification)

Run:  .venv/Scripts/python backend/ingest/build_corpus.py
"""
import json
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).parent))
from build_genes import FIG6, FIG6_CATEGORY  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend" / "data"
INVITRO = ROOT / "data" / "raw" / "Published In vitro KB paper.pdf"
REVIEW = ROOT / "data" / "raw" / "Review article - published.pdf"

INVITRO_LABEL = "In-vitro paper"
REVIEW_LABEL = "Review paper"
MAX_CHARS = 1500

genes = json.loads((DATA / "genes.json").read_text(encoding="utf-8"))
# symbol -> gene, covering raw + official symbols
SYMS = {}
for g in genes:
    SYMS[g["symbol"]] = g
    SYMS[g["raw_symbol"]] = g
SYM_RE = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(sorted(map(re.escape, SYMS), key=len, reverse=True)) + r")(?![A-Za-z0-9])")
# a few common spellings used in prose
PROSE = {"caspase 3": "CASP3", "caspase-3": "CASP3", "caspase 9": "CASP9", "caspase-9": "CASP9", "bcl-2": "BCL2",
         "bcl2": "BCL2", "p53": "TP53", "p21": "CDKN1A", "her2": "ERBB2", "vegf": "VEGFA", "interleukin-6": "IL6",
         "interleukin-8": "CXCL8", "il-6": "IL6", "il-8": "CXCL8", "tnf-": "TNF", "c-myc": "MYC", "erk": "MAPK1",
         "jnk": "MAPK8", "igf1r": "IGF1R", "pten": "PTEN", "gsk3": "GSK3B", "p22phox": "p22phox"}


def mentioned(text):
    found = {SYMS[m].get("symbol") for m in SYM_RE.findall(text)}
    low = text.lower()
    for k, v in PROSE.items():
        if k in low and v in SYMS:
            found.add(SYMS[v]["symbol"])
        elif k in low and v == "IGF1R":
            found.add("IGF1R")
    return sorted(found)


chunks = []


def add(source, tier, title, text, page=None, label=None):
    # PDF artefacts: zero-width spaces and soft hyphens (word split across a line break)
    text = text.replace("​", "").replace("­ ", "").replace("­", "")
    text = re.sub(r"[ \t]+", " ", text).strip()
    chunks.append({
        "id": f"c{len(chunks):04d}",
        "source": source,
        "tier": tier,
        "title": title,
        "page": page,
        "citation": label or (f"{source} p.{page}" if page else source),
        "text": text,
        "genes": mentioned(text),
    })


# ---------- 1. gene cards ----------
for g in genes:
    st = {"up": "UPREGULATED", "down": "DOWNREGULATED"}[g["status_after_chemo"]]
    lines = [
        f"Gene: {g['symbol']} ({g['full_name']})."
        + (f" The sheet lists it as '{g['raw_symbol']}'." if g["raw_symbol"] != g["symbol"] else ""),
        f"Functional category: {g['category']}.",
        f"Role in OSCC (sheet 1, literature summary): {g['role']}",
        f"Expected status after chemotherapy (sheet 2, the team's study): {st}.",
        f"Pathways/processes: {', '.join(g['pathways'])}.",
    ]
    if g["drug_data"]:
        d, m = g["drug_data"]
        lines.append(
            f"Measured by RT-PCR in KB cells (in-vitro paper, Fig. 6): docetaxel fold change {d['fold_change']} "
            f"({d['significance']}), methotrexate fold change {m['fold_change']} ({m['significance']}); control = 1.0."
        )
    else:
        lines.append("Not among the 29 genes measured by RT-PCR in the in-vitro paper (status comes from sheet 2 only).")
    if g["sheet_paper_conflict"]:
        lines.append("DISCREPANCY: " + g["sheet_paper_conflict"])
    lines += g["flags"]
    add("Gene card", "A", g["symbol"], " ".join(lines), label=f"Sheet: {g['symbol']}")

# ---------- 2. Fig. 6 table + study facts (not extractable from PDF text) ----------
rows = []
for raw, (dfc, dsig, mfc, msig) in FIG6.items():
    sym = SYMS[raw]["symbol"]
    rows.append(f"{sym} [{FIG6_CATEGORY[raw]}]: DTX {dfc} ({dsig}); MTX {mfc} ({msig})")
add(INVITRO_LABEL, "A", "Fig. 6 RT-PCR fold changes (29 genes)",
    "Fig. 6 of the in-vitro paper: relative expression (fold change vs untreated control = 1.0, normalised to beta-actin, "
    "24 h at IC50) in KB cells treated with docetaxel (DTX, 6.25 nM) or methotrexate (MTX, 100 uM). Significance: ns not "
    "significant, * p<0.05, ** p<0.01, *** p<0.001, **** p<0.0001 (values read from the bar labels). "
    + "; ".join(rows) + ".", page=15, label=f"{INVITRO_LABEL} Fig. 6")

add(INVITRO_LABEL, "A", "Drug study overview",
    "In-vitro paper (Natesan et al., Cell Biochemistry and Biophysics 2025): KB oral cancer cells were treated with "
    "docetaxel (DTX, 1.5-50 nM) and methotrexate (MTX, 25-250 uM). MTT assay IC50 at 24 h: DTX 6.25 nM, MTX 100 uM. "
    "In-silico part: DisGeNET gave 773 OSCC-related genes; SwissTargetPrediction gave 82 DTX/MTX target genes; 18 genes "
    "overlap OSCC with DTX and 18 with MTX; 25 further literature genes were added (43 genes) for ShinyGO enrichment and "
    "STRING/Cytoscape CytoHubba hub-gene analysis. RT-PCR measured 29 genes; western blots showed increased caspases 3, 7 "
    "and 9; DNA fragmentation increased; wound-healing migration and colony formation decreased. Authors conclude DTX "
    "showed a significantly stronger cytotoxic effect than MTX.", page=1, label=f"{INVITRO_LABEL} p.1")

disc = [g for g in genes if g["sheet_paper_conflict"]]
add("Data check", "A", "Sheet 2 vs in-vitro paper discrepancies",
    "Discrepancies, conflicts and mismatches: which genes differ, disagree or are inconsistent between the sheet and the paper. "
    "Genes where sheet 2 (expected status after chemotherapy) disagrees with the in-vitro paper's Fig. 6: "
    + " ".join(f"{g['symbol']}: {g['sheet_paper_conflict']}" for g in disc)
    + " Also, the paper's Results text lists XPC and MSH2 among downregulated DNA-repair genes and CDKN1A among "
      "downregulated cell-cycle regulators, while the Fig. 6 bars show XPC and MSH2 increased and CDKN1A increased with "
      "DTX (1.28, *); the text and figure should be reconciled by the authors (PTEN is down in both). TP53 and RB1 are not significant with DTX; CDKN1A, AURKA are not significant "
      "with MTX; PDGFB is not significant with MTX.", label="Data check: sheet vs paper")

# ---------- 3. review Table 3 (chemotherapy resistance biomarkers), entered as structured rows ----------
T3 = [
    ("Cisplatin", "LRRC8A (VRAC influx pump) and SLC31A1 (CTR1) uptake transporter", "Downregulated", "Reduced cisplatin accumulation inside the cell (Siemer et al. 2021)."),
    ("Cisplatin", "KEAP1", "Downregulated", "Loss of KEAP1 leads to constitutive NRF2 expression supporting tumour cell proliferation (Osman et al. 2023)."),
    ("Cisplatin", "SLC40A1 (ferroportin)", "Upregulated", "Continuous iron expulsion reduces ROS-mediated cell damage; resistance (Yu et al. 2020)."),
    ("Cisplatin", "ABCB1 (MDR1)", "Upregulated", "Over-expression expels the drug, causing resistance."),
    ("Cisplatin", "LRP1B", "Downregulated", "Promotes metastasis through deregulated MMPs (Shaikh et al. 2023)."),
    ("Cisplatin", "GSTM1", "Upregulated", "Glutathione S-transferase upregulation reduces ROS, leading to drug resistance (Ferreira et al. 2023)."),
    ("Cisplatin", "HDAC1 and ZEB1", "Upregulated", "ZEB1 is an EMT promoter (Lima De Oliveira et al. 2023)."),
    ("Cisplatin", "LUM, DCN, IL1A, NRG1, TLE4, AKT2, PKD2, PDGF-C, PDE3B, BACH1", "Upregulated", "Include PDGF-C (transforming/tumorigenic PDGF ligand), NRG1 (HER ligand; HER2 overexpression renders cisplatin resistance) (Yamano et al. 2010)."),
    ("Cisplatin", "CD44", "Upregulated (mRNA and protein)", "Linked to DC-mediated tumour immune response (Qiao et al. 2023)."),
    ("Cisplatin", "Stemness markers Nanog, Oct4, Bmi1, CD117, CD133, ABCG2", "Nanog and Oct4 upregulated", "Elevated stemness and tumorigenicity (Tsai et al. 2011)."),
    ("Cisplatin", "APC, GSK3 and MMP7", "APC and GSK3 downregulated, MMP7 upregulated", "Accumulation of cancer stem cells (Milan et al. 2023)."),
    ("Cisplatin", "CEBPA", "Upregulated", "Disrupts IL-17 signalling and cytokine/immune homeostasis in the tumour microenvironment (Qiao et al. 2023)."),
    ("Cisplatin", "p22phox", "Upregulated", "Activates PI3K/AKT, weakens apoptotic signalling, impairs cisplatin nuclear entry (Hung et al. 2015)."),
    ("Cisplatin", "NF-kB", "Upregulated", "Reduced chromatin acetylation and nuclear translocation of BRCA1 (Almeida et al. 2014)."),
    ("5-FU", "WNT5A", "Upregulated", "Regulator of non-canonical WNT pathway that regulates P-gp (Zhang et al. 2024)."),
    ("Cetuximab", "SMAD4", "Upregulated", "Regulator of TGF-beta pathway; increases cancer cell survival (Khattri et al. 2024)."),
    ("Cetuximab", "GPX4", "Downregulated", "Loss removes protection from ROS (Liu et al. 2022b)."),
    ("Paclitaxel and docetaxel", "TOP2A, DNMT1, INHBA and NEK2", "Upregulated", "Involved in DNA repair mechanisms (Khera et al. 2023)."),
    ("Paclitaxel and docetaxel", "FCGBP", "Downregulated", "ncRNA-related downregulation of FCGBP (Ding et al. 2024)."),
]
for drug, marker, status, effect in T3:
    page = 23 if drug in ("Paclitaxel and docetaxel",) else 22
    add(REVIEW_LABEL, "B", f"Table 3: {drug} resistance - {marker}",
        f"Review Table 3 (genes involved in chemotherapy drug resistance of HNSCC). Drug: {drug}. Biomarker for "
        f"resistance: {marker}. Status of the gene: {status}. Effect: {effect}", page=page,
        label=f"{REVIEW_LABEL} Table 3")


# ---------- 4. paper text, page-aware ----------
def paper_chunks(pdf, label, tier, last_page_text_cut=True):
    doc = fitz.open(pdf)
    out_pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        m = re.search(r"^\s*References\s*$", text, re.M)
        if m:
            text = text[: m.start()]
            out_pages.append((i + 1, text))
            break
        out_pages.append((i + 1, text))
    for pno, text in out_pages:
        text = re.sub(r"-\n(?=[a-z])", "", text)  # de-hyphenate
        text = re.sub(r"\n(?=[a-z,;(])", " ", text)  # join wrapped lines
        paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n+", text)]
        paras = [p for p in paras if len(p) > 25]
        buf = ""
        for p in paras:
            if buf and len(buf) + len(p) > MAX_CHARS:
                add(label, tier, f"{label} p.{pno}", buf, page=pno)
                buf = buf[-200:] + " "  # small overlap
            buf += p + " "
        if len(buf.strip()) > 80:
            add(label, tier, f"{label} p.{pno}", buf, page=pno)


paper_chunks(INVITRO, INVITRO_LABEL, "A")
paper_chunks(REVIEW, REVIEW_LABEL, "B")

with open(DATA / "corpus.jsonl", "w", encoding="utf-8") as f:
    for c in chunks:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

from collections import Counter
print(len(chunks), "chunks", Counter(c["source"] for c in chunks))
print("avg chars", sum(len(c["text"]) for c in chunks) // len(chunks), "max", max(len(c["text"]) for c in chunks))

(DATA / "table3.json").write_text(json.dumps(
    [{"drug": d, "biomarker": m, "status": s, "effect": e, "page": 23 if d == "Paclitaxel and docetaxel" else 22,
      "panel_genes": mentioned(m)} for d, m, s, e in T3], indent=2, ensure_ascii=False), encoding="utf-8")
