import { useApi } from '../api'

export default function About() {
  const { data: h } = useApi('/api/health')
  return (
    <div className="grid">
      <div className="card">
        <h2>Where the data comes from</h2>
        <table>
          <tbody>
            <tr><td><span className="tier A">A</span></td><td><b>The team's own study</b>: sheet 2 "gene status after chemotherapy" and the in-vitro paper (docetaxel and methotrexate in KB cells, Natesan et al., Cell Biochem Biophys 2025). Fig. 6 fold changes were read from the bar labels.</td></tr>
            <tr><td><span className="tier B">B</span></td><td><b>The review paper</b> (Natesan et al., Mol Genet Genomics 2026) including Table 3 on chemotherapy-resistance genes.</td></tr>
            <tr><td><span className="tier C">C</span></td><td><b>Sheet 1 "Role in OSCC"</b>: literature summaries. The sheet itself says to verify them against primary sources before citing.</td></tr>
          </tbody>
        </table>
      </div>
      <div className="card">
        <h2>Things to know</h2>
        <ul>
          <li>Sheet 2 gives one direction per gene. The paper measured 29 genes separately for docetaxel (DTX) and methotrexate (MTX); the other 25 have no per-drug values here.</li>
          <li>Six genes show a conflict between sheet 2 and Fig. 6; see the Overview tab. The paper's text and its figure also disagree for XPC, MSH2 and CDKN1A.</li>
          <li>Sheet symbols IGIFR, CAS9 and CAS3 are not official; they are read as IGF1R, CASP9 and CASP3. Both spellings work in search and chat.</li>
          <li>Pathway tags, gene groups and the pro-survival / pro-death class are app-curated for navigation. They are not from the sheet or the papers; review before citing.</li>
          <li>SLC10A1 is marked exploratory: the sheet notes little established OSCC role.</li>
          <li>Chatbot answers are generated from retrieved passages and tool results with citations. Check the cited source for anything you will publish.</li>
        </ul>
      </div>
      <div className="card">
        <h2>System status</h2>
        {h ? (
          <ul>
            <li>{h.genes} genes, {h.chunks} searchable passages</li>
            <li>Language model: {h.llm ? h.chat_model : 'not configured (retrieval-only mode)'}</li>
            <li>Semantic index: {h.dense_index ? 'ready' : 'not built (keyword search only)'}</li>
          </ul>
        ) : <p className="muted">Loading…</p>}
        <p className="muted small">Research use only; not medical advice.</p>
      </div>
    </div>
  )
}
