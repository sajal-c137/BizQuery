import { useEffect, useMemo, useRef, useState } from 'react'
import { getLogs } from '../services/api'

// pill colors per log level — keep palette consistent with the rest of the UI
const LEVEL_TONE = {
  DEBUG: 'bg-gray-100 text-gray-500',
  INFO: 'bg-indigo-50 text-indigo-700',
  WARNING: 'bg-amber-50 text-amber-700',
  ERROR: 'bg-red-50 text-red-700',
  CRITICAL: 'bg-red-100 text-red-800 font-semibold',
}

const LEVELS = ['ALL', 'DEBUG', 'INFO', 'WARNING', 'ERROR']

// one row in the log list
function LogRow({ entry }) {
  const tone = LEVEL_TONE[entry.level] || LEVEL_TONE.INFO
  return (
    <div className="flex gap-3 px-3 py-1.5 text-[12px] font-mono leading-relaxed border-b border-gray-100 last:border-b-0">
      <span className="text-gray-400 whitespace-nowrap">{entry.time}</span>
      <span className={`inline-block text-[10px] px-1.5 py-0.5 rounded uppercase tracking-wide self-start ${tone}`}>
        {entry.level}
      </span>
      <span className="text-gray-500 whitespace-nowrap">{entry.name}</span>
      {/* preserve newlines from tracebacks */}
      <span className="text-gray-800 whitespace-pre-wrap break-words flex-1">{entry.message}</span>
    </div>
  )
}

export default function LogsPage({ onBack }) {
  const [lines, setLines] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  // user-controlled UI state
  const [auto, setAuto] = useState(true)
  const [level, setLevel] = useState('ALL')
  const [paused, setPaused] = useState(false)
  // ref to the scroll container so we can pin to the bottom
  const scrollRef = useRef(null)

  // fetch the latest buffer from the backend
  async function refresh() {
    setLoading(true)
    setError('')
    try {
      const { data } = await getLogs(500)
      setLines(data.lines || [])
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('[logs] fetch failed', err)
      setError(err.response?.data?.detail || 'Failed to load logs')
    } finally {
      setLoading(false)
    }
  }

  // initial load
  useEffect(() => { refresh() }, [])

  // auto-refresh every 3s when enabled and not paused
  useEffect(() => {
    if (!auto || paused) return
    const id = setInterval(refresh, 3000)
    return () => clearInterval(id)
  }, [auto, paused])

  // filter client-side by selected level
  const filtered = useMemo(
    () => (level === 'ALL' ? lines : lines.filter((l) => l.level === level)),
    [lines, level]
  )

  // auto-scroll to the newest line when new logs arrive
  useEffect(() => {
    if (paused) return
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [filtered, paused])

  return (
    <div className="h-full overflow-hidden bg-gray-50 flex flex-col">
      <div className="max-w-5xl mx-auto w-full px-6 py-6 flex-1 min-h-0 flex flex-col">
        {/* header */}
        <header className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Backend Logs</h1>
            <p className="text-sm text-gray-600 mt-1">
              In-memory ring buffer (last {lines.length} lines). Mirrors what{' '}
              <code className="text-[12px] bg-gray-100 px-1 rounded">docker logs</code> sees.
            </p>
          </div>
          <button
            onClick={onBack}
            className="text-sm text-indigo-600 hover:text-indigo-700 whitespace-nowrap"
          >
            ← Back to workspace
          </button>
        </header>

        {/* toolbar */}
        <div className="flex flex-wrap items-center gap-3 mb-3 text-sm">
          {/* level filter */}
          <div className="flex items-center gap-1 bg-white border border-gray-200 rounded-lg p-0.5">
            {LEVELS.map((lv) => (
              <button
                key={lv}
                onClick={() => setLevel(lv)}
                className={`px-2.5 py-1 rounded-md text-[12px] uppercase tracking-wide transition-colors ${
                  level === lv ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:bg-gray-50'
                }`}
              >
                {lv}
              </button>
            ))}
          </div>

          {/* auto-refresh */}
          <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={auto}
              onChange={(e) => setAuto(e.target.checked)}
              className="accent-indigo-600"
            />
            Auto-refresh (3 s)
          </label>

          {/* pause auto-scroll */}
          <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={paused}
              onChange={(e) => setPaused(e.target.checked)}
              className="accent-amber-600"
            />
            Pause scroll
          </label>

          <button
            onClick={refresh}
            disabled={loading}
            className="ml-auto text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-700
                       hover:bg-white hover:border-gray-300 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Refreshing…' : 'Refresh now'}
          </button>
        </div>

        {/* error banner */}
        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2 mb-2">
            {error}
          </p>
        )}

        {/* log viewer */}
        <div
          ref={scrollRef}
          className="flex-1 min-h-0 overflow-y-auto bg-white border border-gray-200 rounded-xl"
        >
          {filtered.length === 0 ? (
            <div className="h-full flex items-center justify-center text-sm text-gray-400 py-10">
              {lines.length === 0 ? 'No logs captured yet.' : `No ${level} entries in the buffer.`}
            </div>
          ) : (
            filtered.map((entry, i) => <LogRow key={i} entry={entry} />)
          )}
        </div>
      </div>
    </div>
  )
}
