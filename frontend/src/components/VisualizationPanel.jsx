import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getCharts } from '../services/api'
import { formatNumber, stripExt } from '../utils/format'

// fixed palette — reused round-robin across charts
const PALETTE = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#06b6d4', '#84cc16']

// single KPI card (sum-style metric)
function KpiCard({ label, value, kind }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
      <div className="text-[11px] uppercase tracking-wide text-gray-400">{label}</div>
      <div className="text-2xl font-semibold text-gray-800 mt-1">
        {formatNumber(value, kind === 'money')}
      </div>
    </div>
  )
}

// recharts wrapper — picks line vs bar by chart.type
function ChartCard({ chart, color }) {
  const { type, title, data, money } = chart
  const fmt = (v) => formatNumber(v, money)
  // pick the chart component based on type
  const Container = type === 'line' ? LineChart : BarChart

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-3">{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <Container data={data} margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
          {/* faint horizontal gridlines only */}
          <CartesianGrid stroke="#f1f1f4" vertical={false} />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 11, fill: '#6b7280' }}
            tickLine={false}
            axisLine={{ stroke: '#e5e7eb' }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#6b7280' }}
            tickLine={false}
            axisLine={{ stroke: '#e5e7eb' }}
            tickFormatter={fmt}
            width={56}
          />
          <Tooltip
            formatter={(v) => fmt(v)}
            contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }}
          />
          {type === 'line' ? (
            <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} />
          ) : (
            <Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} />
          )}
        </Container>
      </ResponsiveContainer>
    </div>
  )
}

// shown when nothing is focused yet
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center text-gray-400 px-6">
      <p className="text-3xl mb-2">📊</p>
      <p className="text-sm">Select a dataset on the left to view its visualizations.</p>
    </div>
  )
}

// shown when a document is focused (no charts for docs)
function DocumentView({ doc }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 px-6">
      <p className="text-3xl mb-2">📄</p>
      <p className="text-base font-medium text-gray-700">{stripExt(doc.filename)}</p>
      <p className="text-sm text-gray-400 mt-1">
        Documents are queryable through the chat — ask a question on the right.
      </p>
    </div>
  )
}

export default function VisualizationPanel({ focused, admin }) {
  // chart bundle returned by /analytics/charts/:id
  const [bundle, setBundle] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // fetch charts whenever the focused CSV (or admin flag) changes
  useEffect(() => {
    // not a CSV? clear the panel and bail
    if (!focused || focused.kind !== 'csv') {
      setBundle(null)
      return
    }

    // 'cancelled' guards against race on rapid focus changes
    let cancelled = false
    setLoading(true)
    setError('')

    getCharts(focused.id, admin)
      .then(({ data }) => {
        if (!cancelled) setBundle(data)
      })
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.error('[viz] failed to load charts', err)
        if (!cancelled) {
          setError(err.response?.data?.detail || 'Failed to load charts')
          setBundle(null)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    // cleanup — drop late responses
    return () => { cancelled = true }
  }, [focused, admin])

  // ---- render branches ----
  if (!focused) return <EmptyState />
  if (focused.kind === 'doc') return <DocumentView doc={focused} />

  return (
    <div className="h-full overflow-y-auto px-6 py-5 bg-gray-50">
      {/* header: dataset name + row count */}
      <header className="mb-4">
        <h2 className="text-lg font-semibold text-gray-800 capitalize">
          {focused.id.replace(/_/g, ' ')}
        </h2>
        <p className="text-xs text-gray-400 mt-0.5">
          {bundle ? `${bundle.row_count.toLocaleString()} rows` : ' '}
        </p>
      </header>

      {/* loading + error states */}
      {loading && <p className="text-sm text-gray-400">Loading charts…</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}

      {bundle && (
        <>
          {/* KPI cards */}
          {bundle.kpis?.length > 0 && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
              {bundle.kpis.map((k) => (
                <KpiCard key={k.label} {...k} />
              ))}
            </div>
          )}

          {/* graceful "nothing to chart" message */}
          {bundle.charts?.length === 0 && (
            <p className="text-sm text-gray-400">
              No chartable columns are visible for this dataset
              {!admin ? ' (try Admin mode for internal metrics).' : '.'}
            </p>
          )}

          {/* chart grid — round-robin colors from PALETTE */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {bundle.charts?.map((chart, i) => (
              <ChartCard key={chart.title} chart={chart} color={PALETTE[i % PALETTE.length]} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
