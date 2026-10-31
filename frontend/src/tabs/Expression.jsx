import { useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useApi } from '../api'
import { Loading, Status } from '../ui'

function Tip({ active, payload }) {
  if (!active || !payload?.length) return null
  const r = payload[0].payload
  return (
    <div className="card small" style={{ padding: 10 }}>
      <b>{r.symbol}</b> <span className="muted">{r.paper_category}</span>
      <div>Sheet 2: <Status s={r.sheet_status} /></div>
      <div style={{ color: 'var(--dtx)' }}>DTX: {r.dtx} ({r.dtxSig})</div>
      <div style={{ color: 'var(--mtx)' }}>MTX: {r.mtx} ({r.mtxSig})</div>
      {r.conflict && <div className="chip warn" style={{ whiteSpace: 'normal' }}>⚠ differs from sheet 2</div>}
    </div>
  )
}

export default function Expression({ openGene }) {
  const genes = useApi('/api/genes')
  const study = useApi('/api/drug-study')
  const [sortBy, setSortBy] = useState('category')

  const rows = useMemo(() => {
    if (!study.data) return []
    const r = study.data.rtpcr.map(g => {
      const [d, m] = g.drugs
      return { symbol: g.symbol, paper_category: g.paper_category, sheet_status: g.sheet_status, conflict: g.conflict,
        dtx: d.fold_change, dtxSig: d.significance, mtx: m.fold_change, mtxSig: m.significance,
        dtxLog: Math.log2(d.fold_change), mtxLog: Math.log2(m.fold_change) }
    })
    return sortBy === 'dtx' ? r.sort((a, b) => b.dtxLog - a.dtxLog) : r
  }, [study.data, sortBy])

  const byGroup = useMemo(() => {
    const m = {}
    ;(genes.data || []).forEach(g => (m[g.group] ||= []).push(g))
    return Object.entries(m)
  }, [genes.data])

  return (
    <Loading data={genes.data && study.data} error={genes.error || study.error}>
      <div className="grid">
        <div className="card">
          <h2>Expected status after chemotherapy, by gene group</h2>
          <p className="muted small">Sheet 2 (the team's study). ▲ up, ▼ down. Click a gene for details; ⚠ marks a conflict with Fig. 6.</p>
          {byGroup.map(([group, gs]) => (
            <div key={group} style={{ margin: '10px 0' }}>
              <h3>{group} <span className="muted small">({gs.length})</span></h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {gs.sort((a, b) => a.status_after_chemo.localeCompare(b.status_after_chemo) || a.symbol.localeCompare(b.symbol)).map(g => (
                  <button key={g.symbol} className={`chip ${g.status_after_chemo}`} style={{ border: 0 }} onClick={() => openGene(g.symbol)}
                    title={g.sheet_paper_conflict || g.full_name}>
                    {g.status_after_chemo === 'up' ? '▲' : '▼'} {g.symbol}{g.sheet_paper_conflict ? ' ⚠' : ''}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <h2 style={{ margin: 0, flex: 1 }}>Measured response in KB cells (Fig. 6)</h2>
            <span className="seg" role="group" aria-label="Sort order">
              <button aria-pressed={sortBy === 'category'} onClick={() => setSortBy('category')}>Paper order</button>
              <button aria-pressed={sortBy === 'dtx'} onClick={() => setSortBy('dtx')}>Sort by DTX</button>
            </span>
          </div>
          <p className="muted small">
            log₂ fold change vs untreated control (0 = no change; right = up, left = down). Values were read from the bar labels in the paper's figure.
          </p>
          <div style={{ height: rows.length * 30 + 70 }}>
            <ResponsiveContainer>
              <BarChart data={rows} layout="vertical" margin={{ left: 10, right: 20 }} barGap={2} barCategoryGap={6}>
                <CartesianGrid stroke="var(--line)" horizontal={false} />
                <XAxis type="number" domain={[-4, 4]} ticks={[-4, -2, 0, 2, 4]} stroke="var(--muted)" />
                <YAxis type="category" dataKey="symbol" width={70} tick={{ fontSize: 12, fill: 'var(--ink2)' }} interval={0} />
                <ReferenceLine x={0} stroke="var(--ink2)" />
                <Tooltip content={<Tip />} cursor={{ fill: 'var(--page)' }} />
                <Legend />
                <Bar dataKey="dtxLog" name="Docetaxel (DTX)" fill="var(--dtx)" radius={2} />
                <Bar dataKey="mtxLog" name="Methotrexate (MTX)" fill="var(--mtx)" radius={2} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </Loading>
  )
}
