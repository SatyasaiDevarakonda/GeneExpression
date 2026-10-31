import { statusGlyph, statusText } from './api'

export function Status({ s }) {
  return <span className={`chip ${s}`}>{statusGlyph(s)} {statusText(s)}</span>
}

export function Loading({ data, error, children }) {
  if (error) return <div className="card">Could not load data: {error}. Is the backend running on port 8000?</div>
  if (!data) return <div className="card muted">Loading…</div>
  return children
}

export function AskButton({ ask, q, children = 'Ask the chatbot', gene }) {
  return <button className="btn small" onClick={() => ask(q, gene)}>💬 {children}</button>
}

export function Sig({ s }) {
  return <span className="muted small">{s === 'ns' ? 'n.s.' : s}</span>
}
