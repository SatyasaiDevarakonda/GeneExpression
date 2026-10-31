import { useEffect, useState } from 'react'

const cache = {}

export function useApi(path) {
  const [data, setData] = useState(cache[path] ?? null)
  const [error, setError] = useState(null)
  useEffect(() => {
    if (cache[path]) return
    let live = true
    fetch(path)
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`${r.status} ${r.statusText}`))))
      .then(d => { cache[path] = d; if (live) setData(d) })
      .catch(e => live && setError(e.message))
    return () => { live = false }
  }, [path])
  return { data, error }
}

export const statusText = s => (s === 'up' ? 'Up' : s === 'down' ? 'Down' : 'n.s.')
export const statusGlyph = s => (s === 'up' ? '▲' : s === 'down' ? '▼' : '–')

/** Streams /api/chat server-sent events. onEvent receives each parsed event. */
export async function streamChat(body, onEvent, signal) {
  const r = await fetch('/api/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal,
  })
  if (!r.ok || !r.body) {
    const detail = await r.json().then(j => j.detail, () => null)
    throw new Error(typeof detail === 'string' ? detail : `Chat request failed (${r.status})`)
  }
  const reader = r.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    let i
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const line = buf.slice(0, i).trim()
      buf = buf.slice(i + 2)
      if (line.startsWith('data:')) {
        try { onEvent(JSON.parse(line.slice(5))) } catch { /* ignore a malformed frame */ }
      }
    }
  }
}
