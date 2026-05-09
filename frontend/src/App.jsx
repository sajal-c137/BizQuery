import { useState } from 'react'
import SourcePanel from './components/SourcePanel'
import VisualizationPanel from './components/VisualizationPanel'
import ChatPanel from './components/ChatPanel'
import DocsPage from './components/DocsPage'
import LogsPage from './components/LogsPage'

// top-bar view switcher options
const VIEWS = [
  { id: 'workspace', label: 'Workspace' },
  { id: 'docs', label: 'Docs' },
  { id: 'logs', label: 'Logs' },
]

export default function App() {
  // checked CSV ids (used by chat as data sources)
  const [selectedCsvs, setSelectedCsvs] = useState([])
  // checked document filenames
  const [selectedDocs, setSelectedDocs] = useState([])
  // currently focused row in the source panel — drives the viz panel
  const [focused, setFocused] = useState(null)
  // admin toggle reveals 'internal' columns and confidential docs
  const [admin, setAdmin] = useState(false)
  // 'workspace' | 'docs' | 'logs'
  const [view, setView] = useState('workspace')

  // toggle helpers — flip an id in/out of the selected list
  const toggleCsv = (id) =>
    setSelectedCsvs((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    )

  const toggleDoc = (name) =>
    setSelectedDocs((prev) =>
      prev.includes(name) ? prev.filter((s) => s !== name) : [...prev, name]
    )

  return (
    <div className="h-screen w-screen flex flex-col bg-gray-50 text-gray-800">
      {/* top bar — title + view switcher */}
      <header className="px-6 py-3 bg-white border-b border-gray-200 flex items-center justify-between">
        <div>
          <h1 className="text-base font-bold text-gray-900">BizQuery</h1>
          <p className="text-[11px] text-gray-500 leading-none mt-0.5">
            AI-powered business analytics workspace
          </p>
        </div>
        {/* segmented control: workspace / docs / logs */}
        <nav className="flex items-center gap-1 bg-gray-50 border border-gray-200 rounded-lg p-0.5">
          {VIEWS.map((v) => (
            <button
              key={v.id}
              onClick={() => setView(v.id)}
              className={`text-sm px-3 py-1 rounded-md transition-colors ${
                view === v.id
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {v.label}
            </button>
          ))}
        </nav>
      </header>

      {view === 'docs' ? (
        // standalone docs view — no sidebars
        <main className="flex-1 min-h-0 overflow-hidden">
          <DocsPage onBack={() => setView('workspace')} />
        </main>
      ) : view === 'logs' ? (
        // standalone logs view — no sidebars
        <main className="flex-1 min-h-0 overflow-hidden">
          <LogsPage onBack={() => setView('workspace')} />
        </main>
      ) : (
        // workspace: sources | viz | chat
        <div className="flex-1 grid grid-cols-[260px_minmax(0,1fr)_380px] min-h-0">
          <SourcePanel
            selectedCsvs={selectedCsvs}
            selectedDocs={selectedDocs}
            onToggleCsv={toggleCsv}
            onToggleDoc={toggleDoc}
            onSetCsvs={setSelectedCsvs}
            onSetDocs={setSelectedDocs}
            focused={focused}
            onFocus={setFocused}
            admin={admin}
            onAdminChange={setAdmin}
          />
          <main className="min-w-0 min-h-0 overflow-hidden">
            <VisualizationPanel focused={focused} admin={admin} />
          </main>
          <ChatPanel selectedCsvs={selectedCsvs} admin={admin} />
        </div>
      )}
    </div>
  )
}
