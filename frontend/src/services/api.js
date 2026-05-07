import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

export const sendMessage = (message, conversationId = null) =>
  api.post('/chat/message', { message, conversation_id: conversationId })

export const getConversations = () =>
  api.get('/chat/conversations')

export const getConversation = (id) =>
  api.get(`/chat/conversations/${id}`)

export default api
