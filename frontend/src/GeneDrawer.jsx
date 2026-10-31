import { useApi } from './api'
import { Sig, Status } from './ui'

export default function GeneDrawer({ symbol, onClose, ask }) {
  const { data: g } = useApi(`/api/genes/${encodeURIComponent(symbol)}`)
  return (
    <>
      <div className="drawer-bg" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label={`${symbol} details`}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'start' }}>
          <h2 style={{ flex: 1 }}>{symbol}</h2>
          <button className="btn small" onClick={onClose} aria-label="Close">✕</button>
        </div>
        {!g ? <p className="muted">Loading…</p> : (
          <>
            <p>{g.full_name}</p>
            <p><Status s={g.status_after_chemo} /> <span className="muted small">expected after chemotherapy (sheet 2, tier A)</span></p>
            {g.sheet_paper_conflict && <p className="chip warn" style={{ whiteSpace: 'normal' }}>⚠ {g.sheet_paper_conflict}</p>}
            {g.flags.map(f => <p key={f} className="chip warn" style={{ whiteSpace: 'normal' }}>{f}</p>)}
            <dl>
              <dt>Category</dt><dd>{g.category}</dd>
              <dt>Group</dt><dd>{g.group}</dd>
              <dt>Pathways</dt><dd>{g.pathways.join(', ')}</dd>
              <dt>Role in OSCC</dt><dd>{g.role} <span className="muted small">(sheet 1, tier C: verify against primary sources)</span></dd>
              <dt>Class (app-curated)</dt><dd>{g.functional_class}</dd>
            </dl>
            <h3>In-vitro RT-PCR (KB cells)</h3>
            {g.drug_data.length === 0 ? <p className="muted small">Not measured in the in-vitro paper; status comes from sheet 2 only.</p> : (
              <table>
                <thead><tr><th>Drug</th><th>Fold change</th><th>Significance</th><th>Direction</th></tr></thead>
                <tbody>{g.drug_data.map(d => (
                  <tr key={d.drug}><td>{d.drug}</td><td>{d.fold_change}</td><td><Sig s={d.significance} /></td><td><Status s={d.direction} /></td></tr>
                ))}</tbody>
              </table>
            )}
            <p style={{ marginTop: 16 }}><button className="btn primary" onClick={() => { onClose(); ask(`What does the data say about ${g.symbol}?`, g.symbol) }}>💬 Ask about {g.symbol}</button></p>
          </>
        )}
      </aside>
    </>
  )
}
