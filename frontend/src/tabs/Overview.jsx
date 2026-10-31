import { Bar, BarChart, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useApi } from '../api'
import { AskButton, Loading } from '../ui'

export default function Overview({ openGene, ask }) {
  const { data, error } = useApi('/api/overview')
  return (
    <Loading data={data} error={error}>
      {data && (
        <div className="grid">
          <div className="grid cols3">
            <div className="card"><div className="stat">{data.total}</div><div className="stat-label">genes in the OSCC panel</div></div>
            <div className="card"><div className="stat" style={{ color: 'var(--down)' }}>▼ {data.down}</div><div className="stat-label">expected to go down after chemotherapy</div></div>
            <div className="card"><div className="stat" style={{ color: 'var(--up)' }}>▲ {data.up}</div><div className="stat-label">expected to go up</div></div>
            <div className="card"><div className="stat">{data.measured_in_paper}</div><div className="stat-label">measured by RT-PCR in the in-vitro paper</div></div>
          </div>

          <div className="card">
            <h2>Headline findings</h2>
            <ul>{data.headlines.map(h => <li key={h}>{h}</li>)}</ul>
            <AskButton ask={ask} q="Summarise the main findings of the study in a few sentences." >Summarise the study</AskButton>
          </div>

          <div className="grid cols2">
            <div className="card">
              <h2>Status after chemotherapy</h2>
              <div style={{ height: 260 }}>
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={[{ name: 'Down', value: data.down }, { name: 'Up', value: data.up }]} dataKey="value" innerRadius={60} outerRadius={95}
                      paddingAngle={2} stroke="var(--surface)" strokeWidth={2} label={({ name, value }) => `${name} ${value}`}>
                      <Cell fill="var(--down)" /><Cell fill="var(--up)" />
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="card">
              <h2>Up vs down by gene group</h2>
              <div style={{ height: 300 }}>
                <ResponsiveContainer>
                  <BarChart data={data.groups} layout="vertical" margin={{ left: 10 }}>
                    <XAxis type="number" allowDecimals={false} stroke="var(--muted)" />
                    <YAxis type="category" dataKey="group" width={150} tick={{ fontSize: 11, fill: 'var(--ink2)' }} />
                    <Tooltip cursor={{ fill: 'var(--page)' }} />
                    <Legend />
                    <Bar dataKey="down" name="▼ Down" stackId="a" fill="var(--down)" stroke="var(--surface)" strokeWidth={2} />
                    <Bar dataKey="up" name="▲ Up" stackId="a" fill="var(--up)" stroke="var(--surface)" strokeWidth={2} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="card">
            <h2>Sheet vs paper: genes to double-check</h2>
            <p className="muted small">
              For these genes the expected status in sheet 2 conflicts with the RT-PCR values in Fig. 6 of the in-vitro paper
              (read from the bar labels). Worth reconciling before publication or sharing.
            </p>
            <div className="table-wrap"><table>
              <thead><tr><th>Gene</th><th>Detail</th><th></th></tr></thead>
              <tbody>{data.discrepancies.map(d => (
                <tr key={d.symbol} className="clickable" onClick={() => openGene(d.symbol)}>
                  <td><b>{d.symbol}</b></td><td>{d.text}</td>
                  <td><button className="btn small" onClick={e => { e.stopPropagation(); ask(`Why might ${d.symbol} differ between sheet 2 and the in-vitro paper?`, d.symbol) }}>💬 Ask</button></td>
                </tr>
              ))}</tbody>
            </table></div>
          </div>
        </div>
      )}
    </Loading>
  )
}
