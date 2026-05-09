import { useEffect, useRef, useState } from 'react'
import { sendMessage } from '../services/api'
import { stripExt } from '../utils/format'

function Message({ role, content, sources }) {
  const isUser = role === 'user'
  const csvs = sources?.csvs ?? []
  const docs = sources?.documents ?? []
  const hasSources = !isUser && (csvs.length > 0 || docs.length > 0)
  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} mb-3`}>
      <div
        className={`max-w-[85%] px-4 py-2 rounded-2xl text-sm leading-relaxed
          ${isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-gray-100 text-gray-800 rounded-bl-sm'}`}
      >
        {content}
      </div>
      {hasSources && (
        <div className="mt-1 max-w-[85%] flex flex-wrap gap-1.5 text-[11px] text-gray-500">
          <span className="font-medium text-gray-400">Sources:</span>
          {csvs.map((id) => (
            <span key={`csv-${id}`} className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100">
              {id}
            </span>
          ))}
          {docs.map((name) => (
            <span key={`doc-${name}`} className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-100">
              {stripExt(name)}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ChatPanel({ selectedCsvs, admin }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend() {
    const text = input.trim()
    if (!text || loading) return

    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setInput('')
    setLoading(true)

    try {
      const { data } = await sendMessage(text, conversationId, selectedCsvs, admin)
      setConversationId(data.conversation_id)
      setMessages((prev) => [...prev, data.message])
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Something went wrong. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const sourceHint =
    selectedCsvs.length === 0
      ? 'No dataset selected — answers will use general knowledge or documents.'
      : `Querying ${selectedCsvs.length} dataset${selectedCsvs.length > 1 ? 's' : ''}: ${selectedCsvs.join(', ')}`

  return (
    <section className="flex flex-col h-full bg-white border-l border-gray-200">
      <header className="px-5 py-3 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-800">Chat</h2>
        <p className="text-[11px] text-gray-400 mt-0.5 truncate" title={sourceHint}>
          {sourceHint}
        </p>
      </header>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-400">
            <p className="text-2xl mb-2">👋</p>
            <p className="text-sm">Ask a question about your data or documents.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <Message key={i} role={m.role} content={m.content} sources={m.sources} />
        ))}
        {loading && (
          <div className="flex justify-start mb-3">
            <div className="bg-gray-100 text-gray-400 px-4 py-2 rounded-2xl rounded-bl-sm text-sm">
              Thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="px-5 py-3 border-t border-gray-200">
        <div className="flex items-end gap-2">
          <textarea
            className="flex-1 resize-none rounded-xl border border-gray-300 px-3 py-2 text-sm
                       focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                       max-h-32"
            rows={1}
            placeholder="Type a message…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed
                       text-white rounded-xl px-4 py-2 text-sm font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </section>
  )
}
