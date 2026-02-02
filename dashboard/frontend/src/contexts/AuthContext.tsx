import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { getUserInfo, isAuthenticated, login as authLogin, logout as authLogout, type UserInfo } from '../services/auth'

interface AuthContextType {
  user: UserInfo | null
  isLoading: boolean
  isAdmin: boolean
  login: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    try {
      const authenticated = await isAuthenticated()
      if (authenticated) {
        const userInfo = await getUserInfo()
        setUser(userInfo)
      }
    } catch (error) {
      console.error('Auth check failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const login = async () => {
    await authLogin()
  }

  const logout = async () => {
    await authLogout()
    setUser(null)
  }

  // Check if user is admin based on groups
  const isAdmin = user?.groups?.includes('admin') ?? false

  const value: AuthContextType = {
    user,
    isLoading,
    isAdmin,
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
