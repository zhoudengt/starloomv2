import axios from 'axios'
import { useUserStore } from '../stores/userStore'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120_000,
})

api.interceptors.request.use((config) => {
  const token = useUserStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
