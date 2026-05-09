import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

export const sendMessage = (message, conversationId = null, sourceIds = null, admin = false) =>
  api.post('/chat/message', {
    message,
    conversation_id: conversationId,
    source_ids: sourceIds && sourceIds.length ? sourceIds : null,
    admin,
  })

export const getSources = () =>
  api.get('/analytics/sources')

export const getCharts = (sourceId, admin = false) =>
  api.get(`/analytics/charts/${sourceId}`, { params: { admin } })

export const getDocuments = () =>
  api.get('/documents/')

export const uploadDocument = (file, sensitivity = 'public') => {
  const form = new FormData()
  form.append('file', file)
  form.append('sensitivity', sensitivity)
  return api.post('/documents/ingest', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const deleteDocument = (docId) =>
  api.delete(`/documents/${docId}`)

export const getConversations = () =>
  api.get('/chat/conversations')

export const getConversation = (id) =>
  api.get(`/chat/conversations/${id}`)

export default api
