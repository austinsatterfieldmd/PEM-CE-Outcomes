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

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { getUserRole, isSupabaseMode } from '../services/apiRouter'
import { onAuthStateChange } from '../services/supabase'

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

  const fetchRole = useCallback(async () => {
    if (!isSupabaseMode) {
      // Local dev with FastAPI — default to admin (full access)
      setRole('admin')
      setIsLoading(false)
      return
    }

    try {
      const userRole = await getUserRole()
      console.log('[RoleContext] Fetched role:', userRole)
      setRole((userRole as UserRole) || 'user')
    } catch (error) {
      console.warn('[RoleContext] Failed to fetch user role, defaulting to read-only:', error)
      setRole('user')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchRole()
  }, [fetchRole])

  // Re-fetch role when auth state changes (e.g., after login)
  useEffect(() => {
    if (!isSupabaseMode) return

    const unsubscribe = onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
        console.log('[RoleContext] Auth state changed:', event, '— re-fetching role')
        // Small delay to ensure session is fully established
        setTimeout(() => fetchRole(), 500)
      }
    })

    return () => unsubscribe()
  }, [fetchRole])

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
