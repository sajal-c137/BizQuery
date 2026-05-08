import { useState, useRef, useEffect } from 'react'
import { sendMessage, getSources } from '../services/api'

function Message({ role, content, sources }) {
  const isUser = role === 'user'
  const csvs = sources?.csvs ?? []
  const docs = sources?.documents ?? []
  const hasSources = !isUser && (csvs.length > 0 || docs.length > 0)
  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} mb-3`}>
      <div
        className={`max-w-[70%] px-4 py-2 rounded-2xl text-sm leading-relaxed
          ${isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-gray-100 text-gray-800 rounded-bl-sm'
          }`}
      >
        {content}
      </div>
      {hasSources && (
        <div className="mt-1 max-w-[70%] flex flex-wrap gap-1.5 text-[11px] text-gray-500">
          <span className="font-medium text-gray-400">Sources:</span>
          {csvs.map((id) => (
            <span key={`csv-${id}`} className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100">
              {id}
            </span>
          ))}
          {docs.map((name) => (
            <span key={`doc-${name}`} className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-100">
              {name.replace(/\.[^/.]+$/, '')}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ChatWindow() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const [sources, setSources] = useState([])
  const [sourceId, setSourceId] = useState('auto')
  const bottomRef = useRef(null)

  useEffect(() => {
    getSources()
      .then(({ data }) => setSources(data))
      .catch(() => {})
  }, [])

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
      const { data } = await sendMessage(text, conversationId, sourceId || null)
      setConversationId(data.conversation_id)
      setMessages((prev) => [...prev, data.message])
    } catch (err) {
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

  return (
    <div className="flex flex-col h-screen bg-white">

      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-white flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-800">BizQuery</h1>
          <p className="text-xs text-gray-400">AI-powered business assistant</p>
        </div>
        {sources.length > 0 && (
          <select
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 text-gray-700
                       focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          >
            <option value="auto">Auto-select sources</option>
            <option value="">No data source</option>
            {sources.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-400">
            <p className="text-2xl mb-2">👋</p>
            <p className="text-sm">Ask me anything about your business data.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <Message key={i} role={msg.role} content={msg.content} sources={msg.sources} />
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

      {/* Input */}
      <div className="px-6 py-4 border-t border-gray-200 bg-white">
        <div className="flex items-end gap-3">
          <textarea
            className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-2 text-sm
                       focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                       max-h-32"
            rows={1}
            placeholder="Type a message… (Enter to send)"
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

    </div>
  )
}
