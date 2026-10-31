import { useMemo, useState } from 'react'
import { useApi } from '../api'
import { Loading } from '../ui'

export default function Literature({ openGene, ask }) {
  const { data, error } = useApi('/api/literature')
  const [q, setQ] = useState('')
  const [src, setSrc] = useState('')
  const needle = q.toLowerCase()

  const t3 = useMemo(() => (data?.table3 || []).filter(r => !needle || JSON.stringify(r).toLowerCase().includes(needle)), [data, needle])
  const chunks = useMemo(() => (data?.chunks || [])
    .filter(c => (!src || c.source === src) && (!needle || c.text.toLowerCase().includes(needle)))
    .slice(0, 40), [data, needle, src])

  return (
    <Loading data={data} error={error}>
      <div className="filters">
        <input type="search" placeholder="Search the papers and Table 3…" value={q} onChange={e => setQ(e.target.value)} aria-label="Search literature" />
        <select value={src} onChange={e => setSrc(e.target.value)} aria-label="Source filter">
          <option value="">Both papers</option><option>In-vitro paper</option><option>Review paper</option>
        </select>
      </div>
      <div className="card" style={{ marginBottom: 16 }}>
        <h2>Chemotherapy-resistance biomarkers in HNSCC <span className="tier B">Tier B</span></h2>
        <p className="muted small">Table 3 of the review (Natesan et al., Mol Genet Genomics 2026), PDF pp. 22–23. Panel genes are clickable.</p>
        <div className="table-wrap"><table>
          <thead><tr><th>Drug</th><th>Biomarker</th><th>Status</th><th>Effect</th></tr></thead>
          <tbody>{t3.map((r, i) => (
            <tr key={i}>
              <td>{r.drug}</td>
              <td>{r.biomarker} {r.panel_genes.map(g => <button key={g} className="chip ns" style={{ border: 0 }} onClick={() => openGene(g)}>{g} ↗</button>)}</td>
              <td>{r.status}</td><td>{r.effect}</td>
            </tr>
          ))}</tbody>
        </table></div>
      </div>
      <h2>Passages ({chunks.length}{chunks.length === 40 ? '+' : ''})</h2>
      <div className="grid">
        {chunks.map(c => (
          <div className="card" key={c.id}>
            <div className="small" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              <span className={`tier ${c.source === 'Review paper' ? 'B' : 'A'}`}>{c.source === 'Review paper' ? 'B' : 'A'}</span>
              <b>{c.source}</b> <span className="muted">PDF p.{c.page}</span>
              {c.genes.slice(0, 8).map(g => <button key={g} className="chip ns" style={{ border: 0 }} onClick={() => openGene(g)}>{g}</button>)}
              <button className="btn small" style={{ marginLeft: 'auto' }} onClick={() => ask(`Summarise this passage from the ${c.source} (p.${c.page}): ${c.text.slice(0, 150)}…`)}>💬 Explain</button>
            </div>
            <p style={{ marginBottom: 0 }}>{c.text}</p>
          </div>
        ))}
      </div>
    </Loading>
  )
}
