import { useState } from 'react'
import SourcePanel from './components/SourcePanel'
import VisualizationPanel from './components/VisualizationPanel'
import ChatPanel from './components/ChatPanel'
import DocsPage from './components/DocsPage'

export default function App() {
  // checked CSV ids (used by chat as data sources)
  const [selectedCsvs, setSelectedCsvs] = useState([])
  // checked document filenames
  const [selectedDocs, setSelectedDocs] = useState([])
  // currently focused row in the source panel — drives the viz panel
  const [focused, setFocused] = useState(null)
  // admin toggle reveals 'internal' columns and confidential docs
  const [admin, setAdmin] = useState(false)
  // 'workspace' | 'docs'
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
        <button
          onClick={() => setView(view === 'docs' ? 'workspace' : 'docs')}
          className="text-sm px-3 py-1.5 rounded-lg border border-gray-200 text-gray-700
                     hover:bg-gray-50 hover:border-gray-300 transition-colors"
        >
          {view === 'docs' ? 'Workspace' : 'Docs'}
        </button>
      </header>

      {view === 'docs' ? (
        // standalone docs view — no sidebars
        <main className="flex-1 min-h-0 overflow-hidden">
          <DocsPage onBack={() => setView('workspace')} />
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
