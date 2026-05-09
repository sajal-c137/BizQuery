import { useEffect, useMemo, useRef, useState } from 'react'
import { getSources, getDocuments, uploadDocument, deleteDocument } from '../services/api'
import { stripExt } from '../utils/format'

function SelectAllCheckbox({ total, selected, onToggle, accent = 'indigo' }) {
  const ref = useRef(null)
  const all = total > 0 && selected === total
  const some = selected > 0 && selected < total
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = some
  }, [some])
  const accentClass = accent === 'amber' ? 'accent-amber-600' : 'accent-indigo-600'
  return (
    <input
      ref={ref}
      type="checkbox"
      checked={all}
      disabled={total === 0}
      onChange={() => onToggle(!all)}
      title={all ? 'Deselect all' : 'Select all'}
      className={`${accentClass} cursor-pointer disabled:cursor-not-allowed disabled:opacity-40`}
    />
  )
}

export default function SourcePanel({
  selectedCsvs,
  selectedDocs,
  onToggleCsv,
  onToggleDoc,
  onSetCsvs,
  onSetDocs,
  focused,
  onFocus,
  admin,
  onAdminChange,
}) {
  const [csvs, setCsvs] = useState([])
  const [docs, setDocs] = useState([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const fileInput = useRef(null)

  const ingestedDocs = useMemo(() => docs.filter((d) => d.status === 'ingested'), [docs])

  async function refresh() {
    try {
      const [s, d] = await Promise.all([getSources(), getDocuments()])
      setCsvs(s.data)
      setDocs(d.data)
    } catch {
      // backend may be starting up; ignore
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  async function handleUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setError('')
    try {
      await uploadDocument(file)
      await refresh()
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  async function handleDelete(docId) {
    try {
      await deleteDocument(docId)
      await refresh()
    } catch {
      setError('Delete failed')
    }
  }

  const isFocusedCsv = (id) => focused?.kind === 'csv' && focused.id === id
  const isFocusedDoc = (id) => focused?.kind === 'doc' && focused.id === id

  return (
    <aside className="flex flex-col h-full bg-white border-r border-gray-200">
      <div className="px-4 py-4 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-800">Sources</h2>
        <p className="text-xs text-gray-400 mt-0.5">Pick what the assistant should use</p>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-5">
        <section>
          <div className="px-1 mb-1.5 flex items-center justify-between">
            <label className="flex items-center gap-2 cursor-pointer">
              <SelectAllCheckbox
                total={csvs.length}
                selected={selectedCsvs.length}
                onToggle={(on) => onSetCsvs(on ? csvs.map((s) => s.id) : [])}
              />
              <span className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                Datasets
              </span>
            </label>
            <span className="text-[11px] text-gray-400">{csvs.length}</span>
          </div>
          <ul className="space-y-1">
            {csvs.map((s) => {
              const checked = selectedCsvs.includes(s.id)
              const focusedRow = isFocusedCsv(s.id)
              return (
                <li key={s.id}>
                  <div
                    className={`group flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors
                      ${focusedRow
                        ? 'bg-indigo-50 border border-indigo-200'
                        : 'border border-transparent hover:bg-gray-50'}`}
                    onClick={() => onFocus({ kind: 'csv', id: s.id })}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => onToggleCsv(s.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="accent-indigo-600 cursor-pointer"
                    />
                    <span className="text-sm text-gray-700 truncate flex-1">{s.name}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded
                      ${focusedRow ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-500'}`}>
                      csv
                    </span>
                  </div>
                </li>
              )
            })}
          </ul>
        </section>

        <section>
          <div className="px-1 mb-1.5 flex items-center justify-between">
            <label className="flex items-center gap-2 cursor-pointer">
              <SelectAllCheckbox
                total={ingestedDocs.length}
                selected={selectedDocs.length}
                onToggle={(on) => onSetDocs(on ? ingestedDocs.map((d) => d.filename) : [])}
                accent="amber"
              />
              <span className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                Documents
              </span>
            </label>
            <span className="text-[11px] text-gray-400">{docs.length}</span>
          </div>
          <ul className="space-y-1">
            {docs.length === 0 && (
              <li className="px-2 py-3 text-xs text-gray-400">No documents yet.</li>
            )}
            {docs.map((d) => {
              const checked = selectedDocs.includes(d.filename)
              const focusedRow = isFocusedDoc(d.doc_id)
              return (
                <li key={d.doc_id}>
                  <div
                    className={`group flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors
                      ${focusedRow
                        ? 'bg-amber-50 border border-amber-200'
                        : 'border border-transparent hover:bg-gray-50'}`}
                    onClick={() => onFocus({ kind: 'doc', id: d.doc_id, filename: d.filename })}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => onToggleDoc(d.filename)}
                      onClick={(e) => e.stopPropagation()}
                      className="accent-amber-600 cursor-pointer"
                      disabled={d.status !== 'ingested'}
                    />
                    <span className="text-sm text-gray-700 truncate flex-1">{stripExt(d.filename)}</span>
                    {d.status !== 'ingested' ? (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-600">
                        {d.status}
                      </span>
                    ) : (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded
                        ${focusedRow ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-500'}`}>
                        {d.file_type}
                      </span>
                    )}
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(d.doc_id) }}
                      className="opacity-0 group-hover:opacity-100 text-[11px] text-gray-400 hover:text-red-500"
                      title="Delete"
                    >
                      ✕
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        </section>
      </div>

      <div className="px-3 py-3 border-t border-gray-200 space-y-2">
        <label className="flex items-center gap-2 text-xs cursor-pointer">
          <input
            type="checkbox"
            checked={admin}
            onChange={(e) => onAdminChange(e.target.checked)}
            className="accent-amber-600"
          />
          <span className={`flex-1 ${admin ? 'text-amber-700 font-medium' : 'text-gray-600'}`}>
            Admin mode
          </span>
          <span className="text-[10px] text-gray-400">internal metrics</span>
        </label>

        <input
          ref={fileInput}
          type="file"
          accept=".pdf,.txt,.md"
          onChange={handleUpload}
          className="hidden"
        />
        <button
          onClick={() => fileInput.current?.click()}
          disabled={uploading}
          className="w-full text-sm bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50
                     text-white rounded-lg py-1.5 transition-colors"
        >
          {uploading ? 'Uploading…' : '+ Add document'}
        </button>
        {error && <p className="text-[11px] text-red-500">{error}</p>}
      </div>
    </aside>
  )
}
