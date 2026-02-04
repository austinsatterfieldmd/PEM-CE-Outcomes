/**
 * Authentication Service
 *
 * Provides login, logout, and token management for the CME Dashboard.
 * Uses Supabase SSO with SAML for Okta integration.
 *
 * NOTE: For local development, set VITE_DISABLE_AUTH=true in .env to bypass authentication
 */

import {
  getSupabaseClient,
  isSupabaseConfigured,
  isSSOConfigured,
  signInWithSSO,
  handleAuthCallback as handleSupabaseCallback,
  getSession,
  getUser,
  signOut,
  onAuthStateChange,
  getAccessToken as getSupabaseToken
} from './supabase'

// Development mode helper - bypasses auth for local testing
export function isDevMode(): boolean {
  // Explicit disable via env var
  if (import.meta.env.VITE_DISABLE_AUTH === 'true') {
    return true
  }
  // Dev mode with no auth configured
  if (import.meta.env.DEV) {
    return true
  }
  // Production but Supabase not configured - bypass auth gracefully
  if (!isSupabaseConfigured()) {
    return true
  }
  return false
}

/**
 * Check if SSO is properly configured
 * (Replaces isOktaConfigured)
 */
export function isOktaConfigured(): boolean {
  return isSSOConfigured()
}

/**
 * Redirect to Okta login via Supabase SSO
 */
export async function login(): Promise<void> {
  const { error } = await signInWithSSO()
  if (error) {
    throw error
  }
  // User will be redirected to Okta
}

/**
 * Handle the callback from SSO after login
 */
export async function handleLoginCallback(): Promise<void> {
  const { session, error } = await handleSupabaseCallback()
  if (error) {
    throw error
  }
  if (!session) {
    throw new Error('No session returned from callback')
  }
}

/**
 * Check if user is authenticated
 */
export async function isAuthenticated(): Promise<boolean> {
  if (isDevMode()) {
    return true
  }

  const session = await getSession()
  return session !== null
}

/**
 * Get the current auth state
 */
export async function getAuthState(): Promise<{ isAuthenticated: boolean }> {
  const session = await getSession()
  return { isAuthenticated: session !== null }
}

/**
 * Get the access token for API calls
 */
export async function getAccessToken(): Promise<string | undefined> {
  if (isDevMode()) {
    return undefined
  }

  const token = await getSupabaseToken()
  return token || undefined
}

/**
 * Get user information from Supabase session
 */
export async function getUserInfo(): Promise<UserInfo | null> {
  if (isDevMode()) {
    return {
      sub: 'dev-user',
      email: 'dev@localhost',
      name: 'Development User',
      groups: ['admin']
    }
  }

  const user = await getUser()
  if (!user) {
    return null
  }

  // Extract user metadata from Supabase user object
  const metadata = user.user_metadata || {}

  return {
    sub: user.id,
    email: user.email || '',
    name: metadata.name || metadata.full_name || metadata.first_name || user.email?.split('@')[0] || '',
    groups: metadata.groups || []
  }
}

/**
 * Logout the user
 */
export async function logout(): Promise<void> {
  await signOut()
  // Redirect to login page
  window.location.href = '/'
}

/**
 * Subscribe to auth state changes
 */
export function subscribeToAuthState(callback: (state: { isAuthenticated?: boolean }) => void): () => void {
  return onAuthStateChange((_event, session) => {
    callback({ isAuthenticated: session !== null })
  })
}

/**
 * Refresh tokens if needed (Supabase handles this automatically)
 */
export async function refreshTokens(): Promise<void> {
  // Supabase auto-refreshes tokens, but we can force a refresh
  const supabase = getSupabaseClient()
  await supabase.auth.refreshSession()
}

// Types
export interface UserInfo {
  sub: string
  email: string
  name: string
  groups: string[]
}

// Auth context for React
export interface AuthContextType {
  isAuthenticated: boolean
  isLoading: boolean
  user: UserInfo | null
  isAdmin: boolean
  login: () => Promise<void>
  logout: () => Promise<void>
  getAccessToken: () => Promise<string | undefined>
}

/**
 * Get auth headers for API requests
 */
export async function getAuthHeaders(): Promise<Record<string, string>> {
  if (isDevMode()) {
    return {}
  }

  const token = await getAccessToken()
  if (token) {
    return { Authorization: `Bearer ${token}` }
  }

  return {}
}

// Cached current user for synchronous access
let cachedCurrentUser: UserInfo | null = null

/**
 * Set the cached current user (called by AuthProvider)
 */
export function setCachedUser(user: UserInfo | null): void {
  cachedCurrentUser = user
}

/**
 * Get current user synchronously (from cache)
 * Returns null if user hasn't been loaded yet
 */
export function getCurrentUser(): UserInfo | null {
  if (isDevMode()) {
    return {
      sub: 'dev-user',
      email: 'dev@localhost',
      name: 'Development User',
      groups: ['admin']
    }
  }
  return cachedCurrentUser
}
