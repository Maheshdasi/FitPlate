const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')
const TOKEN_KEY = 'fitplate_token'

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export class ApiError extends Error {
  constructor(message, status, errors) {
    super(message)
    this.status = status
    this.errors = errors || []
  }
}

/** Today's date in the user's own timezone, as YYYY-MM-DD. */
export function localDate(d = new Date()) {
  const off = d.getTimezoneOffset() * 60000
  return new Date(d.getTime() - off).toISOString().slice(0, 10)
}

let onUnauthorized = () => {}
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn }

export async function api(path, { method = 'GET', body, params } = {}) {
  const url = new URL(API_URL + path)
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v)
  })
  const headers = { 'Content-Type': 'application/json' }
  const token = tokenStore.get()
  if (token) headers.Authorization = `Bearer ${token}`

  let res
  try {
    res = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined })
  } catch {
    throw new ApiError('Cannot reach the server. Check that the backend is running.', 0)
  }

  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized()
    const detail = typeof data?.detail === 'string' ? data.detail : 'Something went wrong. Please try again.'
    throw new ApiError(detail, res.status, data?.errors)
  }
  return data
}

export const get = (path, params) => api(path, { params })
export const post = (path, body, params) => api(path, { method: 'POST', body, params })
export const put = (path, body) => api(path, { method: 'PUT', body })
export const del = (path, params) => api(path, { method: 'DELETE', params })
