import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { get, post, setUnauthorizedHandler, tokenStore } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(tokenStore.get()))

  const logout = useCallback(() => {
    tokenStore.clear()
    setUser(null)
  }, [])

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) { setLoading(false); return null }
    try {
      const me = await get('/auth/me')
      setUser(me)
      return me
    } catch {
      logout()
      return null
    } finally {
      setLoading(false)
    }
  }, [logout])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    refresh()
  }, [refresh, logout])

  const authenticate = async (path, email, password) => {
    const res = await post(path, { email, password })
    tokenStore.set(res.access_token)
    const me = await get('/auth/me')
    setUser(me)
    return me
  }

  const value = useMemo(() => ({
    user,
    loading,
    login: (e, p) => authenticate('/auth/login', e, p),
    register: (e, p) => authenticate('/auth/register', e, p),
    logout,
    refresh,
    markProfileComplete: (name) => setUser((u) => ({ ...u, has_profile: true, name })),
  }), [user, loading, logout, refresh])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
