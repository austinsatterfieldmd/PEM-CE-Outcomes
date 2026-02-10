/**
 * Supabase Client for Vite/React SPA
 *
 * Creates a Supabase client for browser-side authentication.
 * Uses Supabase SSO with SAML for Okta integration.
 */

import { createClient, SupabaseClient, User, Session } from '@supabase/supabase-js'

// Supabase configuration from environment variables
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || ''
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || ''
const SSO_PROVIDER_ID = import.meta.env.VITE_SSO_PROVIDER_ID || ''

// Validate configuration
export function isSupabaseConfigured(): boolean {
  return (
    SUPABASE_URL !== '' &&
    SUPABASE_URL !== 'https://your-project-ref.supabase.co' &&
    SUPABASE_ANON_KEY !== '' &&
    SUPABASE_ANON_KEY !== 'your-anon-key-here'
  )
}

export function isSSOConfigured(): boolean {
  return (
    isSupabaseConfigured() &&
    SSO_PROVIDER_ID !== '' &&
    SSO_PROVIDER_ID !== 'your-sso-provider-id-here'
  )
}

// Create singleton Supabase client
let supabaseClient: SupabaseClient | null = null

export function getSupabaseClient(): SupabaseClient {
  if (!supabaseClient) {
    if (!isSupabaseConfigured()) {
      console.warn('Supabase not configured. Auth will be disabled.')
    }
    supabaseClient = createClient(
      SUPABASE_URL || 'https://placeholder.supabase.co',
      SUPABASE_ANON_KEY || 'placeholder-key',
      {
        auth: {
          autoRefreshToken: true,
          persistSession: true,
          detectSessionInUrl: false,
          flowType: 'pkce'
        }
      }
    )
  }
  return supabaseClient
}

/**
 * Sign in with Okta SSO via Supabase SAML
 */
export async function signInWithSSO(): Promise<{ error: Error | null }> {
  if (!isSSOConfigured()) {
    return { error: new Error('SSO not configured. Please set VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, and VITE_SSO_PROVIDER_ID.') }
  }

  const supabase = getSupabaseClient()
  const callbackUrl = import.meta.env.VITE_AUTH_CALLBACK_URL || window.location.origin

  const { error } = await supabase.auth.signInWithSSO({
    providerId: SSO_PROVIDER_ID,
    options: {
      redirectTo: `${callbackUrl}/auth/callback`
    }
  })

  return { error: error ? new Error(error.message) : null }
}

/**
 * Handle the auth callback - exchange code for session
 * Supabase PKCE flow puts the code in query params (?code=xxx)
 * Also check hash fragments as fallback
 */
export async function handleAuthCallback(): Promise<{ session: Session | null; error: Error | null }> {
  const supabase = getSupabaseClient()

  // Get the code from URL query params (PKCE flow)
  const params = new URLSearchParams(window.location.search)
  const code = params.get('code')

  if (code) {
    const { data, error } = await supabase.auth.exchangeCodeForSession(code)
    if (error) {
      return { session: null, error: new Error(error.message) }
    }
    return { session: data.session, error: null }
  }

  // Fallback: check if session was already set (e.g., via hash fragment)
  const { data: { session }, error } = await supabase.auth.getSession()
  if (error) {
    return { session: null, error: new Error(error.message) }
  }
  if (session) {
    return { session, error: null }
  }

  return { session: null, error: new Error('No authorization code in callback URL') }
}

/**
 * Get current session
 */
export async function getSession(): Promise<Session | null> {
  const supabase = getSupabaseClient()
  const { data: { session } } = await supabase.auth.getSession()
  return session
}

/**
 * Get current user
 */
export async function getUser(): Promise<User | null> {
  const supabase = getSupabaseClient()
  const { data: { user } } = await supabase.auth.getUser()
  return user
}

/**
 * Sign out
 */
export async function signOut(): Promise<void> {
  const supabase = getSupabaseClient()
  await supabase.auth.signOut()
}

/**
 * Subscribe to auth state changes
 */
export function onAuthStateChange(callback: (event: string, session: Session | null) => void): () => void {
  const supabase = getSupabaseClient()
  const { data: { subscription } } = supabase.auth.onAuthStateChange(callback)
  return () => subscription.unsubscribe()
}

/**
 * Get access token for API calls
 */
export async function getAccessToken(): Promise<string | null> {
  const session = await getSession()
  return session?.access_token || null
}
