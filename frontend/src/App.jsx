import { useEffect, useState } from 'react'
import Chat, { useChat } from './Chat'
import GeneDrawer from './GeneDrawer'
import { useApi } from './api'
import Overview from './tabs/Overview'
import GeneTable from './tabs/GeneTable'
import Expression from './tabs/Expression'
import Pathways from './tabs/Pathways'
import Network from './tabs/Network'
import DrugStudy from './tabs/DrugStudy'
import Literature from './tabs/Literature'
import About from './tabs/About'

const TABS = [
  ['overview', 'Overview', Overview], ['genes', 'Gene table', GeneTable], ['expression', 'Expression response', Expression],
  ['pathways', 'Pathways', Pathways], ['network', 'Network', Network], ['drugs', 'Drug study', DrugStudy],
  ['literature', 'Literature', Literature], ['chat', 'Chatbot', null], ['about', 'About & data', About],
]

const initialTab = () => TABS.find(t => t[0] === location.hash.slice(1))?.[0] || 'overview'

export default function App() {
  const [tab, setTab] = useState(initialTab)
  const [drawer, setDrawer] = useState(null)
  const [dock, setDock] = useState(false)
  const [focusGene, setFocusGene] = useState(null)
  const [theme, setTheme] = useState(() => { try { return localStorage.getItem('theme') } catch { return null } })
  const chat = useChat()
  const { data: health } = useApi('/api/health')

  useEffect(() => { location.hash = tab }, [tab])
  useEffect(() => {
    const root = document.documentElement
    theme ? root.setAttribute('data-theme', theme) : root.removeAttribute('data-theme')
    try { theme ? localStorage.setItem('theme', theme) : localStorage.removeItem('theme') } catch { /* storage unavailable */ }
  }, [theme])

  const ask = (q, gene) => {
    setFocusGene(gene || null)
    if (tab !== 'chat') setDock(true)
    chat.send(q, gene)
  }
  const dark = theme ? theme === 'dark' : window.matchMedia?.('(prefers-color-scheme: dark)').matches
  const Current = TABS.find(t => t[0] === tab)[2]
  const docked = dock && tab !== 'chat'

  return (
    <div className={`app ${docked ? 'chat-open' : ''}`}>
      <div className="main">
        <header className="top">
          <div className="brand">OSCC Gene Explorer<small>Gene expression after chemotherapy in oral squamous cell carcinoma</small></div>
          <button className="btn" onClick={() => setDock(d => !d)} aria-pressed={docked}>💬 {docked ? 'Hide chat' : 'Chat'}</button>
          <button className="btn" onClick={() => setTheme(dark ? 'light' : 'dark')} aria-label="Toggle dark mode">{dark ? '☀ Light' : '☾ Dark'}</button>
        </header>
        <nav className="tabs" role="tablist">
          {TABS.map(([id, label]) => (
            <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}>{label}</button>
          ))}
        </nav>
        <main className="content">
          <div className="disclaimer">Research-use only. This dashboard summarises a study dataset and published literature; it is not medical advice.</div>
          {tab === 'chat'
            ? <Chat chat={chat} focusGene={focusGene} page health={health} />
            : <Current openGene={setDrawer} ask={ask} goto={setTab} />}
        </main>
      </div>
      {docked && <Chat chat={chat} focusGene={focusGene} onClose={() => setDock(false)} health={health} />}
      {drawer && <GeneDrawer symbol={drawer} onClose={() => setDrawer(null)} ask={ask} />}
    </div>
  )
}
