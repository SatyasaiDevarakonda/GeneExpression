import { useCallback, useEffect, useRef, useState } from 'react'
import { streamChat } from './api'

export function useChat() {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState('technical')
  const abort = useRef(null)

  const send = useCallback(async (text, focusGene) => {
    text = text.trim()
    if (!text || loading) return
    const history = messages.map(m => ({ role: m.role, content: m.content }))
    setMessages(m => [...m, { role: 'user', content: text }, { role: 'assistant', content: '', sources: [] }])
    setLoading(true)
    const patch = fn => setMessages(ms => ms.map((m, i) => (i === ms.length - 1 ? fn(m) : m)))
    abort.current = new AbortController()
    try {
      await streamChat({ message: text, history, mode, focus_gene: focusGene || null }, ev => {
        if (ev.type === 'sources') patch(m => ({ ...m, sources: [...m.sources, ...ev.sources.filter(s => !m.sources.some(x => x.label === s.label))] }))
        else if (ev.type === 'token') patch(m => ({ ...m, content: m.content + ev.text }))
        else if (ev.type === 'error') patch(m => ({ ...m, error: ev.message }))
      }, abort.current.signal)
    } catch (e) {
      if (e.name !== 'AbortError') patch(m => ({ ...m, error: e.message }))
    } finally {
      setLoading(false)
    }
  }, [messages, loading, mode])

  const clear = () => { abort.current?.abort(); setMessages([]); setLoading(false) }
  return { messages, loading, mode, setMode, send, clear }
}

function Message({ m }) {
  const [open, setOpen] = useState(null)
  if (m.role === 'user') return <div className="msg user">{m.content}</div>
  const parts = m.content.split(/(\[[^\[\]]+\])/g)
  const byLabel = Object.fromEntries((m.sources || []).map(s => [s.label, s]))
  const openSrc = open && byLabel[open]
  return (
    <div className="msg bot">
      {parts.map((p, i) => {
        const label = p.startsWith('[') ? p.slice(1, -1) : null
        if (label && byLabel[label]) {
          return <button key={i} className="cite" onClick={() => setOpen(open === label ? null : label)}>{label}</button>
        }
        return <span key={i}>{p}</span>
      })}
      {!m.content && !m.error && <span className="muted">Thinking…</span>}
      {m.error && <div className="chip warn" style={{ whiteSpace: 'normal' }}>{m.error}</div>}
      {openSrc && (
        <div className="excerpt">
          <span className={`tier ${openSrc.tier}`}>Tier {openSrc.tier}</span> <b>{openSrc.label}</b>
          <div>{openSrc.excerpt}{openSrc.excerpt.length >= 600 ? '…' : ''}</div>
        </div>
      )}
    </div>
  )
}

const SUGGESTIONS = [
  'Which genes are upregulated after chemotherapy?',
  'Which genes disagree between the sheet and the paper?',
  'Compare docetaxel and methotrexate in KB cells',
  'What does ERCC1 do in OSCC?',
  'Which PI3K/AKT genes go down?',
]

export default function Chat({ chat, focusGene, onClose, page, health }) {
  const [text, setText] = useState('')
  const log = useRef(null)
  useEffect(() => { log.current?.scrollTo({ top: log.current.scrollHeight }) }, [chat.messages])
  const submit = e => { e.preventDefault(); chat.send(text, focusGene); setText('') }
  return (
    <aside className={`chat ${page ? 'page' : ''}`} aria-label="Chatbot">
      <div className="chat-head">
        <b>Ask the data</b>
        <span className="muted small">{health?.llm ? 'Gemini + RAG' : 'retrieval-only (no API key)'}</span>
        <span style={{ marginLeft: 'auto' }} className="seg" role="group" aria-label="Answer style">
          <button aria-pressed={chat.mode === 'technical'} onClick={() => chat.setMode('technical')}>Technical</button>
          <button aria-pressed={chat.mode === 'simple'} onClick={() => chat.setMode('simple')}>Simple</button>
        </span>
        <button className="btn small" onClick={chat.clear}>Clear</button>
        {onClose && <button className="btn small" onClick={onClose} aria-label="Close chat">✕</button>}
      </div>
      <div className="chat-log" ref={log}>
        {chat.messages.length === 0 && (
          <div className="muted small">
            Answers come only from your gene sheet and the two papers, with clickable citations.
            Research use only; not medical advice.
          </div>
        )}
        {chat.messages.map((m, i) => <Message key={i} m={m} />)}
      </div>
      {chat.messages.length === 0 && (
        <div className="suggest">{SUGGESTIONS.map(s => <button key={s} onClick={() => chat.send(s, focusGene)}>{s}</button>)}</div>
      )}
      <form className="chat-form" onSubmit={submit}>
        <input value={text} onChange={e => setText(e.target.value)} maxLength={2000}
          placeholder={focusGene ? `Ask about ${focusGene}…` : 'Ask about a gene, pathway or drug…'} aria-label="Your question" />
        <button className="btn primary" disabled={chat.loading || !text.trim()}>Send</button>
      </form>
    </aside>
  )
}
