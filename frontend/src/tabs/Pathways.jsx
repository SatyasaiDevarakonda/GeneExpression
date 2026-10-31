import { useApi } from '../api'
import { AskButton, Loading } from '../ui'

export default function Pathways({ openGene, ask }) {
  const { data, error } = useApi('/api/pathways')
  return (
    <Loading data={data} error={error}>
      <p className="muted small">
        Genes grouped by pathway or process (curated from the sheet's categories and the pathways named in the review).
        A gene can belong to several pathways. Bars show how many genes are expected to go down (blue) or up (orange).
      </p>
      <div className="grid cols2">
        {data?.map(p => (
          <div className="card" key={p.name}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
              <h2 style={{ flex: 1 }}>{p.name}</h2>
              <span className="muted small">{p.n} genes</span>
            </div>
            <div className="bar-track" role="img" aria-label={`${p.down.length} down, ${p.up.length} up`} style={{ height: 16 }}>
              <span style={{ width: `${(p.down.length / p.n) * 100}%`, background: 'var(--down)' }} />
              <span style={{ width: `${(p.up.length / p.n) * 100}%`, background: 'var(--up)' }} />
            </div>
            <p className="small" style={{ margin: '8px 0' }}>
              <b style={{ color: 'var(--down)' }}>▼ {p.down.length}</b> down · <b style={{ color: 'var(--up)' }}>▲ {p.up.length}</b> up
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
              {[...p.down.map(s => [s, 'down']), ...p.up.map(s => [s, 'up'])].map(([s, st]) => (
                <button key={s} className={`chip ${st}`} style={{ border: 0 }} onClick={() => openGene(s)}>{st === 'up' ? '▲' : '▼'} {s}</button>
              ))}
            </div>
            <p style={{ marginBottom: 0 }}><AskButton ask={ask} q={`Summarise what happens to ${p.name} genes after chemotherapy.`}>Summarise</AskButton></p>
          </div>
        ))}
      </div>
    </Loading>
  )
}
