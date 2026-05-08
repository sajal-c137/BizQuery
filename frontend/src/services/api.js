import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

export const sendMessage = (message, conversationId = null, sourceId = null, admin = false) =>
  api.post('/chat/message', {
    message,
    conversation_id: conversationId,
    source_id: sourceId || undefined,
    admin,
  })

export const getSources = () =>
  api.get('/analytics/sources')

export const getConversations = () =>
  api.get('/chat/conversations')

export const getConversation = (id) =>
  api.get(`/chat/conversations/${id}`)

export default api
