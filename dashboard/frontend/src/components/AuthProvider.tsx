import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import {
  isAuthenticated,
  getUserInfo,
  login,
  logout,
  subscribeToAuthState,
  isDevMode,
  UserInfo,
  AuthContextType,
} from '../services/auth';
import { LoginPage, LoginCallback } from './LoginPage';

// Create auth context
const AuthContext = createContext<AuthContextType | null>(null);

// Hook to use auth context
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [authState, setAuthState] = useState<{
    isAuthenticated: boolean;
    isLoading: boolean;
    user: UserInfo | null;
  }>({
    isAuthenticated: false,
    isLoading: true,
    user: null,
  });

  // Check if we're on the login callback route
  const isLoginCallback = window.location.pathname === '/login/callback';

  useEffect(() => {
    // Skip auth check in dev mode
    if (isDevMode()) {
      setAuthState({
        isAuthenticated: true,
        isLoading: false,
        user: {
          sub: 'dev-user',
          email: 'dev@example.com',
          name: 'Development User',
          groups: ['admin'],
        },
      });
      return;
    }

    // Don't check auth state on callback route
    if (isLoginCallback) {
      return;
    }

    // Initial auth check
    const checkAuth = async () => {
      try {
        const authenticated = await isAuthenticated();
        if (authenticated) {
          const user = await getUserInfo();
          setAuthState({
            isAuthenticated: true,
            isLoading: false,
            user,
          });
        } else {
          setAuthState({
            isAuthenticated: false,
            isLoading: false,
            user: null,
          });
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        setAuthState({
          isAuthenticated: false,
          isLoading: false,
          user: null,
        });
      }
    };

    checkAuth();

    // Subscribe to auth state changes
    const unsubscribe = subscribeToAuthState((state) => {
      if (state.isAuthenticated !== undefined) {
        getUserInfo().then((user) => {
          setAuthState({
            isAuthenticated: state.isAuthenticated ?? false,
            isLoading: false,
            user,
          });
        });
      }
    });

    return () => {
      unsubscribe();
    };
  }, [isLoginCallback]);

  // Handle dev mode login
  const handleDevModeLogin = () => {
    setAuthState({
      isAuthenticated: true,
      isLoading: false,
      user: {
        sub: 'dev-user',
        email: 'dev@example.com',
        name: 'Development User',
        groups: ['admin'],
      },
    });
  };

  // Render login callback handler
  if (isLoginCallback) {
    return <LoginCallback />;
  }

  // Show loading spinner while checking auth
  if (authState.isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <svg
            className="animate-spin h-8 w-8 text-blue-500 mx-auto mb-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <p className="text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Show login page if not authenticated
  if (!authState.isAuthenticated) {
    return <LoginPage onDevModeLogin={import.meta.env.DEV ? handleDevModeLogin : undefined} />;
  }

  // Check if user is admin based on groups
  const isAdmin = authState.user?.groups?.includes('admin') ?? false;

  // Provide auth context to children
  const contextValue: AuthContextType = {
    isAuthenticated: authState.isAuthenticated,
    isLoading: authState.isLoading,
    user: authState.user,
    isAdmin,
    login,
    logout,
    getAccessToken: async () => {
      const { getAccessToken } = await import('../services/auth');
      return getAccessToken();
    },
  };

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
}

/**
 * User info display component for the header
 */
export function UserMenu() {
  const { user, logout } = useAuth();
  const [showMenu, setShowMenu] = useState(false);

  if (!user) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setShowMenu(!showMenu)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/10 transition-colors"
      >
        <div className="w-8 h-8 bg-accent-400 rounded-full flex items-center justify-center text-primary-500 font-bold text-sm">
          {user.name?.[0]?.toUpperCase() || user.email?.[0]?.toUpperCase() || '?'}
        </div>
        <span className="text-sm font-medium text-white hidden md:block">
          {user.name || user.email}
        </span>
      </button>

      {showMenu && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setShowMenu(false)}
          />
          <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-50">
            <div className="px-4 py-2 border-b border-slate-100">
              <p className="text-sm font-medium text-slate-900">{user.name}</p>
              <p className="text-xs text-slate-500">{user.email}</p>
            </div>
            <button
              onClick={() => {
                setShowMenu(false);
                logout();
              }}
              className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
            >
              Sign out
            </button>
          </div>
        </>
      )}
    </div>
  );
}
