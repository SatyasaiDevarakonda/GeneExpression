import cytoscape from 'cytoscape'
import { useEffect, useRef, useState } from 'react'
import { useApi } from '../api'
import { Loading } from '../ui'

const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim()

export default function Network({ openGene }) {
  const { data, error } = useApi('/api/network')
  const box = useRef(null)
  const cy = useRef(null)
  const [hub, setHub] = useState('DTX')
  const [themeTick, setThemeTick] = useState(0)

  useEffect(() => {
    const mo = new MutationObserver(() => setThemeTick(t => t + 1))
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => mo.disconnect()
  }, [])

  useEffect(() => {
    if (!data || !box.current) return
    const hubs = new Set(hub === 'off' ? [] : data.hubs[hub].slice(0, 10).map(h => h[0]))
    const up = css('--up'), down = css('--down'), ink = css('--ink'), line = css('--muted'), surface = css('--surface')
    cy.current?.destroy()
    cy.current = cytoscape({
      container: box.current,
      elements: [
        ...data.nodes.map(n => ({ data: { ...n, label: n.type === 'gene' ? `${n.status === 'up' ? '▲' : '▼'} ${n.id}` : n.id, hub: hubs.has(n.id) ? 1 : 0 } })),
        ...data.edges.map(e => ({ data: e })),
      ],
      style: [
        { selector: 'node', style: { label: 'data(label)', 'font-size': 12, color: ink, 'text-valign': 'center', 'text-halign': 'center',
          'text-outline-color': surface, 'text-outline-width': 2 } },
        { selector: 'node[type="gene"]', style: { shape: 'round-rectangle', width: 74, height: 28, 'border-width': 1, 'border-color': surface,
          'text-valign': 'center' } },
        { selector: 'node[status="up"]', style: { 'background-color': up, 'background-opacity': 0.35, 'border-color': up } },
        { selector: 'node[status="down"]', style: { 'background-color': down, 'background-opacity': 0.35, 'border-color': down } },
        { selector: 'node[hub=1]', style: { 'border-width': 4, 'font-weight': 'bold' } },
        { selector: 'node[type="pathway"]', style: { shape: 'diamond', width: 'mapData(n, 2, 20, 60, 120)', height: 'mapData(n, 2, 20, 40, 70)',
          'background-color': surface, 'border-width': 2, 'border-color': line, 'font-size': 11, 'text-wrap': 'wrap', 'text-max-width': 90 } },
        { selector: 'edge', style: { width: 1, 'line-color': line, opacity: 0.35, 'curve-style': 'haystack' } },
        { selector: '.dim', style: { opacity: 0.12 } },
      ],
      wheelSensitivity: 0.3,
    })
    cy.current.layout({ name: 'cose', animate: false, nodeRepulsion: 9000, idealEdgeLength: 90, randomize: true, numIter: 1200, fit: true, padding: 24 }).run()
    cy.current.fit(undefined, 24)
    cy.current.on('tap', 'node[type="gene"]', e => openGene(e.target.id()))
    cy.current.on('mouseover', 'node', e => {
      const nb = e.target.closedNeighborhood()
      cy.current.elements().not(nb).addClass('dim')
    })
    cy.current.on('mouseout', 'node', () => cy.current.elements().removeClass('dim'))
    return () => { cy.current?.destroy(); cy.current = null }
  }, [data, hub, themeTick, openGene])

  return (
    <Loading data={data} error={error}>
      <div className="filters" style={{ alignItems: 'center' }}>
        <span className="small">Highlight hub genes (top 10 by degree in the paper's PPI analysis):</span>
        <span className="seg" role="group" aria-label="Hub genes">
          {['DTX', 'MTX', 'off'].map(h => <button key={h} aria-pressed={hub === h} onClick={() => setHub(h)}>{h === 'off' ? 'None' : h}</button>)}
        </span>
      </div>
      <div className="legend">
        <span><i style={{ background: 'var(--up)' }} />▲ up after chemo</span>
        <span><i style={{ background: 'var(--down)' }} />▼ down after chemo</span>
        <span>◆ pathway / process</span><span>thick border = hub gene</span>
      </div>
      <div className="net" ref={box} role="img" aria-label="Gene to pathway network. Use the Pathways tab for an accessible list." />
      <p className="muted small">
        Edges link a gene to the pathways it belongs to (curated; not a protein-interaction network). Hub genes come from the
        in-vitro paper's STRING/CytoHubba analysis (EGFR is a hub in the paper but is not in this panel). Hover to focus; click a gene for details.
      </p>
    </Loading>
  )
}
