/**
 * Role Context — Provides RBAC role information from Supabase.
 *
 * Three roles:
 *   admin — Full access + user management
 *   ma    — Full write access (edit tags, review, proposals)
 *   user  — Read-only (default for new users)
 *
 * When Supabase is not enabled, defaults to 'admin' (local dev = full access).
 */

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { getUserRole, isSupabaseMode } from '../services/apiRouter'

type UserRole = 'admin' | 'ma' | 'user'

interface RoleContextType {
  role: UserRole
  isAdmin: boolean
  canEdit: boolean       // admin or ma
  isLoading: boolean
  refreshRole: () => Promise<void>
}

const RoleContext = createContext<RoleContextType | undefined>(undefined)

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<UserRole>(isSupabaseMode ? 'user' : 'admin')
  const [isLoading, setIsLoading] = useState(isSupabaseMode)

  const fetchRole = async () => {
    if (!isSupabaseMode) {
      // Local dev with FastAPI — default to admin (full access)
      setRole('admin')
      setIsLoading(false)
      return
    }

    try {
      const userRole = await getUserRole()
      setRole((userRole as UserRole) || 'user')
    } catch (error) {
      console.warn('Failed to fetch user role, defaulting to read-only:', error)
      setRole('user')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchRole()
  }, [])

  const value: RoleContextType = {
    role,
    isAdmin: role === 'admin',
    canEdit: role === 'admin' || role === 'ma',
    isLoading,
    refreshRole: fetchRole
  }

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>
}

export function useRole() {
  const context = useContext(RoleContext)
  if (context === undefined) {
    throw new Error('useRole must be used within a RoleProvider')
  }
  return context
}
