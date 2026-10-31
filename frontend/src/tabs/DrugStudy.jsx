import { useApi } from '../api'
import { AskButton, Loading, Sig, Status } from '../ui'

export default function DrugStudy({ openGene, ask }) {
  const { data: d, error } = useApi('/api/drug-study')
  return (
    <Loading data={d} error={error}>
      {d && (
        <div className="grid">
          <div className="card">
            <h2>Docetaxel vs methotrexate in KB oral cancer cells</h2>
            <p className="muted small">{d.citation}. {d.model}.</p>
            <div className="grid cols3">
              {d.ic50.map(x => (
                <div key={x.drug}>
                  <div className="stat" style={{ color: x.drug === 'DTX' ? 'var(--dtx)' : 'var(--mtx)' }}>{x.value} {x.unit}</div>
                  <div className="stat-label">{x.name} IC50 ({x.range})</div>
                </div>
              ))}
              <div><div className="stat">{d.insilico.enrichment_genes}</div><div className="stat-label">genes in the in-silico enrichment / PPI analysis</div></div>
            </div>
            <p>{d.conclusion}</p>
            <AskButton ask={ask} q="Compare docetaxel and methotrexate in the KB cell study: potency and gene-expression effects." />
          </div>

          <div className="card">
            <h2>Assays</h2>
            <div className="table-wrap"><table>
              <thead><tr><th>Assay</th><th>Finding</th><th>Figure</th></tr></thead>
              <tbody>{d.assays.map(a => <tr key={a.title}><td><b>{a.title}</b></td><td>{a.finding}</td><td>{a.figure}</td></tr>)}</tbody>
            </table></div>
          </div>

          <div className="card">
            <h2>RT-PCR fold change, 29 genes (Fig. 6)</h2>
            <p className="muted small">Fold change vs untreated control (1.0). Significance stars from the paper; n.s. = not significant. ⚠ = differs from sheet 2.</p>
            <div className="table-wrap"><table>
              <thead><tr><th>Gene</th><th>Paper category</th><th>Sheet 2</th><th style={{ color: 'var(--dtx)' }}>DTX</th><th style={{ color: 'var(--mtx)' }}>MTX</th></tr></thead>
              <tbody>{d.rtpcr.map(r => (
                <tr key={r.symbol} className="clickable" onClick={() => openGene(r.symbol)}>
                  <td><b>{r.symbol}</b> {r.conflict && <span className="chip warn" title={r.conflict}>⚠</span>}</td>
                  <td>{r.paper_category}</td><td><Status s={r.sheet_status} /></td>
                  {r.drugs.map(x => (
                    <td key={x.drug}>{x.fold_change} <Sig s={x.significance} /> <Status s={x.direction} /></td>
                  ))}
                </tr>
              ))}</tbody>
            </table></div>
          </div>

          <div className="grid cols2">
            <div className="card">
              <h2>Hub genes (PPI, top 10 by degree)</h2>
              {['DTX', 'MTX'].map(k => (
                <div key={k} style={{ marginBottom: 10 }}>
                  <h3 style={{ color: k === 'DTX' ? 'var(--dtx)' : 'var(--mtx)' }}>{k}</h3>
                  {d.hub_genes_degree[k].map(([g, n]) => (
                    <div className="bar-row" key={g}>
                      <span>{g}</span>
                      <div className="bar-track"><span style={{ width: `${(n / 37) * 100}%`, background: k === 'DTX' ? 'var(--dtx)' : 'var(--mtx)' }} /></div>
                      <span className="muted">{n}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
            <div className="card">
              <h2>In-silico summary</h2>
              <ul>
                <li>{d.insilico.oscc_genes_disgenet} OSCC-related genes (DisGeNET)</li>
                <li>{d.insilico.drug_targets_swisstarget} drug target genes (SwissTargetPrediction)</li>
                <li>{d.insilico.overlap_dtx} OSCC∩DTX and {d.insilico.overlap_mtx} OSCC∩MTX overlaps</li>
              </ul>
              <p className="muted small">{d.insilico.note}</p>
              <h3>ADMET (partial)</h3>
              <div className="table-wrap"><table>
                <thead><tr><th>Property</th><th>DTX</th><th>MTX</th></tr></thead>
                <tbody>{d.admet.map(a => <tr key={a.property}><td>{a.property}</td><td>{a.DTX}</td><td>{a.MTX}</td></tr>)}</tbody>
              </table></div>
            </div>
          </div>
        </div>
      )}
    </Loading>
  )
}
