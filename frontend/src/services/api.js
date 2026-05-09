import axios from 'axios'

// shared axios instance — nginx forwards /api/* to the backend in docker,
// vite's dev proxy does the same in local dev
const api = axios.create({
  baseURL: '/api',
  // don't let a stuck request hang the UI forever
  timeout: 60_000,
})

// log every non-2xx response so we have a single place to debug API issues
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const url = err.config?.url ?? '?'
    const status = err.response?.status ?? '???'
    const detail = err.response?.data?.detail ?? err.message
    // eslint-disable-next-line no-console
    console.error(`[api] ${status} ${url} — ${detail}`)
    return Promise.reject(err)
  }
)

// ---- chat ----

export const sendMessage = (message, conversationId = null, sourceIds = null, admin = false) =>
  api.post('/chat/message', {
    message,
    conversation_id: conversationId,
    // backend treats empty list as "use no source"; collapse that to null
    source_ids: sourceIds && sourceIds.length ? sourceIds : null,
    admin,
  })

export const getConversations = () =>
  api.get('/chat/conversations')

export const getConversation = (id) =>
  api.get(`/chat/conversations/${id}`)

// ---- analytics ----

export const getSources = () =>
  api.get('/analytics/sources')

export const getCharts = (sourceId, admin = false) =>
  api.get(`/analytics/charts/${sourceId}`, { params: { admin } })

// ---- documents ----

export const getDocuments = () =>
  api.get('/documents/')

export const uploadDocument = (file, sensitivity = 'public') => {
  // multipart upload — backend handles validation + size cap
  const form = new FormData()
  form.append('file', file)
  form.append('sensitivity', sensitivity)
  return api.post('/documents/ingest', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    // file ingestion can take a while (PDF parsing, embedding, chroma write)
    timeout: 120_000,
  })
}

export const deleteDocument = (docId) =>
  api.delete(`/documents/${docId}`)

export default api
