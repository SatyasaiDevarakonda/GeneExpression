import { useMemo, useState } from 'react'
import { useApi } from '../api'
import { Loading, Status } from '../ui'

const COLS = [['symbol', 'Gene'], ['full_name', 'Full name'], ['group', 'Group'], ['status_after_chemo', 'After chemo'], ['measured_in_paper', 'In paper']]

export function downloadCsv(rows, name) {
  const esc = v => `"${String(v ?? '').replace(/"/g, '""')}"`
  const head = Object.keys(rows[0])
  const csv = [head.join(','), ...rows.map(r => head.map(h => esc(r[h])).join(','))].join('\n')
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
  a.download = name
  a.click()
}

export default function GeneTable({ openGene }) {
  const { data, error } = useApi('/api/genes')
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [group, setGroup] = useState('')
  const [pathway, setPathway] = useState('')
  const [sort, setSort] = useState({ key: 'symbol', dir: 1 })

  const rows = useMemo(() => {
    if (!data) return []
    const needle = q.toLowerCase()
    return data
      .filter(g => (!status || g.status_after_chemo === status) && (!group || g.group === group) && (!pathway || g.pathways.includes(pathway)))
      .filter(g => !needle || [g.symbol, g.raw_symbol, g.full_name, g.category, g.role].join(' ').toLowerCase().includes(needle))
      .sort((a, b) => (String(a[sort.key]) > String(b[sort.key]) ? 1 : -1) * sort.dir)
  }, [data, q, status, group, pathway, sort])

  const groups = useMemo(() => [...new Set((data || []).map(g => g.group))], [data])
  const pathways = useMemo(() => [...new Set((data || []).flatMap(g => g.pathways))].sort(), [data])

  return (
    <Loading data={data} error={error}>
      <div className="filters">
        <input type="search" placeholder="Search gene, name or role…" value={q} onChange={e => setQ(e.target.value)} aria-label="Search genes" />
        <select value={status} onChange={e => setStatus(e.target.value)} aria-label="Status filter">
          <option value="">All statuses</option><option value="up">▲ Up</option><option value="down">▼ Down</option>
        </select>
        <select value={group} onChange={e => setGroup(e.target.value)} aria-label="Group filter">
          <option value="">All groups</option>{groups.map(x => <option key={x}>{x}</option>)}
        </select>
        <select value={pathway} onChange={e => setPathway(e.target.value)} aria-label="Pathway filter">
          <option value="">All pathways</option>{pathways.map(x => <option key={x}>{x}</option>)}
        </select>
        <button className="btn" disabled={!rows.length} onClick={() => downloadCsv(rows.map(g => ({
          symbol: g.symbol, sheet_symbol: g.raw_symbol, full_name: g.full_name, group: g.group, category: g.category,
          status_after_chemo: g.status_after_chemo, pathways: g.pathways.join('; '), role: g.role,
        })), 'oscc_genes.csv')}>⬇ CSV</button>
      </div>
      <p className="muted small">{rows.length} of {data?.length} genes. Click a row for details.</p>
      <div className="table-wrap"><table>
        <thead><tr>{COLS.map(([k, label]) => (
          <th key={k} className="sortable" onClick={() => setSort(s => ({ key: k, dir: s.key === k ? -s.dir : 1 }))}
            aria-sort={sort.key === k ? (sort.dir > 0 ? 'ascending' : 'descending') : 'none'}>
            {label}{sort.key === k ? (sort.dir > 0 ? ' ↑' : ' ↓') : ''}
          </th>
        ))}</tr></thead>
        <tbody>{rows.map(g => (
          <tr key={g.symbol} className="clickable" onClick={() => openGene(g.symbol)}>
            <td><b>{g.symbol}</b>{g.raw_symbol !== g.symbol && <span className="muted small"> (sheet: {g.raw_symbol})</span>}</td>
            <td>{g.full_name}</td><td>{g.group}</td>
            <td><Status s={g.status_after_chemo} /> {g.sheet_paper_conflict && <span className="chip warn" title={g.sheet_paper_conflict}>⚠ check</span>}</td>
            <td>{g.measured_in_paper ? 'Yes' : <span className="muted">–</span>}</td>
          </tr>
        ))}</tbody>
      </table></div>
    </Loading>
  )
}
