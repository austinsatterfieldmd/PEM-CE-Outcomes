/**
 * Okta Authentication Service
 *
 * Provides login, logout, and token management for the CME Dashboard.
 * Uses Okta Auth JS SDK for authentication flow.
 *
 * NOTE: For local development, set VITE_DISABLE_AUTH=true in .env to bypass authentication
 */

// Types for when Okta is not installed
type OktaAuth = any;
type AuthState = any;
type TokenResponse = any;

// Development mode helper - bypasses auth for local testing
// Also bypasses auth when Okta is not configured (e.g., initial deployment)
export function isDevMode(): boolean {
  // Explicit disable via env var
  if (import.meta.env.VITE_DISABLE_AUTH === 'true') {
    return true;
  }
  // Dev mode with no auth configured
  if (import.meta.env.DEV) {
    return true;
  }
  // Production but Okta not configured - bypass auth gracefully
  const issuer = import.meta.env.VITE_OKTA_ISSUER;
  const clientId = import.meta.env.VITE_OKTA_CLIENT_ID;
  if (!issuer || !clientId || issuer === 'https://your-org.okta.com/oauth2/default' || clientId === 'your-client-id') {
    return true;
  }
  return false;
}

// Okta configuration from environment variables
const oktaConfig = {
  issuer: import.meta.env.VITE_OKTA_ISSUER || 'https://your-org.okta.com/oauth2/default',
  clientId: import.meta.env.VITE_OKTA_CLIENT_ID || 'your-client-id',
  redirectUri: `${window.location.origin}/login/callback`,
  postLogoutRedirectUri: window.location.origin,
  scopes: ['openid', 'profile', 'email'],
  pkce: true,
};

// Create Okta Auth instance
let oktaAuth: OktaAuth | null = null;

function getOktaAuth(): OktaAuth {
  if (isDevMode()) {
    // Return mock auth object for dev mode
    return {} as OktaAuth;
  }

  if (!oktaAuth) {
    // Only import and initialize Okta in production
    throw new Error('Okta authentication not configured. Please install @okta/okta-auth-js or set VITE_DISABLE_AUTH=true');
  }
  return oktaAuth;
}

/**
 * Check if Okta is properly configured
 */
export function isOktaConfigured(): boolean {
  return (
    oktaConfig.issuer !== 'https://your-org.okta.com/oauth2/default' &&
    oktaConfig.clientId !== 'your-client-id'
  );
}

/**
 * Redirect to Okta login page
 */
export async function login(): Promise<void> {
  const auth = getOktaAuth();
  await auth.signInWithRedirect();
}

/**
 * Handle the callback from Okta after login
 */
export async function handleLoginCallback(): Promise<TokenResponse> {
  const auth = getOktaAuth();
  return auth.handleLoginRedirect();
}

/**
 * Check if user is authenticated
 */
export async function isAuthenticated(): Promise<boolean> {
  if (isDevMode()) {
    return true; // Always authenticated in dev mode
  }
  const auth = getOktaAuth();
  return auth.isAuthenticated();
}

/**
 * Get the current auth state
 */
export function getAuthState(): Promise<AuthState> {
  const auth = getOktaAuth();
  return auth.authStateManager.getAuthState() || Promise.resolve({ isAuthenticated: false });
}

/**
 * Get the access token for API calls
 */
export async function getAccessToken(): Promise<string | undefined> {
  const auth = getOktaAuth();
  const tokenManager = auth.tokenManager;

  try {
    const accessToken = await tokenManager.get('accessToken');
    return accessToken?.accessToken;
  } catch {
    return undefined;
  }
}

/**
 * Get user information from the ID token
 */
export async function getUserInfo(): Promise<UserInfo | null> {
  if (isDevMode()) {
    // Return mock user in dev mode
    return {
      sub: 'dev-user',
      email: 'dev@localhost',
      name: 'Development User',
      groups: ['admin'],
    };
  }

  const auth = getOktaAuth();

  try {
    const idToken = await auth.tokenManager.get('idToken');
    if (idToken && 'claims' in idToken) {
      const claims = idToken.claims as Record<string, unknown>;
      return {
        sub: claims.sub as string,
        email: claims.email as string,
        name: claims.name as string || claims.preferred_username as string,
        groups: claims.groups as string[] || [],
      };
    }
  } catch {
    // Token not available
  }

  return null;
}

/**
 * Logout the user
 */
export async function logout(): Promise<void> {
  const auth = getOktaAuth();
  await auth.signOut();
}

/**
 * Subscribe to auth state changes
 */
export function subscribeToAuthState(callback: (state: AuthState) => void): () => void {
  const auth = getOktaAuth();
  auth.authStateManager.subscribe(callback);

  // Start the auth state service
  auth.start();

  // Return unsubscribe function
  return () => {
    auth.authStateManager.unsubscribe(callback);
  };
}

/**
 * Refresh tokens if needed
 */
export async function refreshTokens(): Promise<void> {
  const auth = getOktaAuth();

  try {
    await auth.tokenManager.renew('accessToken');
    await auth.tokenManager.renew('idToken');
  } catch (error) {
    console.error('Failed to refresh tokens:', error);
    // If refresh fails, redirect to login
    await login();
  }
}

// Types
export interface UserInfo {
  sub: string;
  email: string;
  name: string;
  groups: string[];
}

// Auth context for React
export interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserInfo | null;
  isAdmin: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => Promise<string | undefined>;
}

/**
 * Get auth headers for API requests
 */
export async function getAuthHeaders(): Promise<Record<string, string>> {
  if (isDevMode()) {
    return {};
  }

  const token = await getAccessToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }

  return {};
}
