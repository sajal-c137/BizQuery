import { useEffect, useMemo, useRef, useState } from 'react'
import { getSources, getDocuments, uploadDocument, deleteDocument } from '../services/api'
import { stripExt } from '../utils/format'

// tri-state checkbox: all / some / none
function SelectAllCheckbox({ total, selected, onToggle, accent = 'indigo' }) {
  const ref = useRef(null)
  const all = total > 0 && selected === total
  const some = selected > 0 && selected < total

  // native browsers expose the indeterminate flag only via JS
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
  // available sources (fetched from backend)
  const [csvs, setCsvs] = useState([])
  const [docs, setDocs] = useState([])
  // upload state + last error message
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  // toggle: mark next upload as confidential
  const [confidentialUpload, setConfidentialUpload] = useState(false)
  const fileInput = useRef(null)

  // only ingested docs can be checked / queried in chat
  const ingestedDocs = useMemo(
    () => docs.filter((d) => d.status === 'ingested'),
    [docs]
  )

  // refresh both lists; survives backend startup hiccups
  async function refresh() {
    try {
      const [s, d] = await Promise.all([getSources(), getDocuments()])
      setCsvs(s.data)
      setDocs(d.data)
    } catch (err) {
      // backend may still be booting — log but don't surface to the user
      // eslint-disable-next-line no-console
      console.warn('[sources] refresh failed', err)
    }
  }

  // initial load
  useEffect(() => {
    refresh()
  }, [])

  // user picked a file -> upload + refresh
  async function handleUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError('')
    try {
      await uploadDocument(file, confidentialUpload ? 'internal' : 'public')
      await refresh()
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('[sources] upload failed', err)
      setError(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
      // clear the input so picking the same file again still triggers onChange
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  async function handleDelete(docId) {
    setError('')
    try {
      await deleteDocument(docId)
      await refresh()
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('[sources] delete failed', err)
      setError(err.response?.data?.detail || 'Delete failed')
    }
  }

  // focus helpers — drive the highlight + visualization panel
  const isFocusedCsv = (id) => focused?.kind === 'csv' && focused.id === id
  const isFocusedDoc = (id) => focused?.kind === 'doc' && focused.id === id

  return (
    <aside className="flex flex-col h-full bg-white border-r border-gray-200">
      {/* sidebar header */}
      <div className="px-4 py-4 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-800">Sources</h2>
        <p className="text-xs text-gray-400 mt-0.5">Pick what the assistant should use</p>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-5">
        {/* ---- datasets section ---- */}
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
                  {/* row: clicking anywhere focuses, clicking the box (only) toggles */}
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
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded
                        ${focusedRow ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-500'}`}
                    >
                      csv
                    </span>
                  </div>
                </li>
              )
            })}
          </ul>
        </section>

        {/* ---- documents section ---- */}
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
            {/* empty state */}
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
                      // can't query a doc that isn't fully ingested
                      disabled={d.status !== 'ingested'}
                    />
                    <span className="text-sm text-gray-700 truncate flex-1">
                      {stripExt(d.filename)}
                    </span>

                    {/* confidential badge */}
                    {d.sensitivity === 'internal' && (
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-700 font-medium"
                        title="Confidential — visible only in Admin mode"
                      >
                        confidential
                      </span>
                    )}

                    {/* status / type badge */}
                    {d.status !== 'ingested' ? (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-600">
                        {d.status}
                      </span>
                    ) : (
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded
                          ${focusedRow ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-500'}`}
                      >
                        {d.file_type}
                      </span>
                    )}

                    {/* delete button — only visible on row hover */}
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

      {/* ---- footer: admin toggle + upload ---- */}
      <div className="px-3 py-3 border-t border-gray-200 space-y-2">
        {/* admin mode -> reveal internal columns / docs */}
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

        {/* mark the next upload confidential */}
        <label className="flex items-center gap-2 text-xs cursor-pointer">
          <input
            type="checkbox"
            checked={confidentialUpload}
            onChange={(e) => setConfidentialUpload(e.target.checked)}
            className="accent-red-600"
          />
          <span className={`flex-1 ${confidentialUpload ? 'text-red-700 font-medium' : 'text-gray-600'}`}>
            Mark next upload confidential
          </span>
          <span className="text-[10px] text-gray-400">admin only</span>
        </label>

        {/* hidden file input + button trigger */}
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
          {uploading ? 'Uploading…' : `+ Add ${confidentialUpload ? 'confidential ' : ''}document`}
        </button>

        {/* surfaced error (upload / delete) */}
        {error && <p className="text-[11px] text-red-500">{error}</p>}
      </div>
    </aside>
  )
}
