import { useEffect, useState } from 'react';
import { login, isOktaConfigured } from '../services/auth';
import { LogIn, AlertCircle, Lock } from 'lucide-react';

interface LoginPageProps {
  onDevModeLogin?: () => void;
}

export function LoginPage({ onDevModeLogin }: LoginPageProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isConfigured = isOktaConfigured();
  const isDev = import.meta.env.DEV;

  const handleLogin = async () => {
    setIsLoading(true);
    setError(null);

    try {
      await login();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initiate login');
      setIsLoading(false);
    }
  };

  const handleDevLogin = () => {
    if (onDevModeLogin) {
      onDevModeLogin();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4">
            <Lock className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">CME Question Explorer</h1>
          <p className="text-slate-400 mt-2">Sign in to access the dashboard</p>
        </div>

        {/* Login Card */}
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-2xl p-8 shadow-xl">
          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-400 text-sm font-medium">Login Error</p>
                <p className="text-red-300/80 text-sm mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Okta Not Configured Warning */}
          {!isConfigured && (
            <div className="mb-6 p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-amber-400 text-sm font-medium">Okta Not Configured</p>
                <p className="text-amber-300/80 text-sm mt-1">
                  Set VITE_OKTA_ISSUER and VITE_OKTA_CLIENT_ID environment variables to enable
                  authentication.
                </p>
              </div>
            </div>
          )}

          {/* Login Button */}
          <button
            onClick={handleLogin}
            disabled={isLoading || !isConfigured}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
          >
            {isLoading ? (
              <>
                <svg
                  className="animate-spin h-5 w-5"
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
                <span>Signing in...</span>
              </>
            ) : (
              <>
                <LogIn className="w-5 h-5" />
                <span>Sign in with Okta</span>
              </>
            )}
          </button>

          {/* Dev Mode Login (only in development) */}
          {isDev && onDevModeLogin && (
            <div className="mt-6 pt-6 border-t border-slate-700">
              <p className="text-slate-400 text-xs text-center mb-3">Development Mode</p>
              <button
                onClick={handleDevLogin}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm font-medium rounded-lg transition-colors"
              >
                Skip authentication (dev only)
              </button>
            </div>
          )}

          {/* Footer */}
          <p className="text-slate-500 text-xs text-center mt-6">
            Protected by Okta SSO. Contact your administrator for access.
          </p>
        </div>

        {/* MJH Branding */}
        <p className="text-slate-600 text-xs text-center mt-8">
          MJH Life Sciences &bull; CME Outcomes Analytics
        </p>
      </div>
    </div>
  );
}

/**
 * Login Callback Page - handles the redirect from Okta
 */
export function LoginCallback() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const { handleLoginCallback } = await import('../services/auth');
        await handleLoginCallback();
        // Redirect to main app after successful login
        window.location.href = '/';
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Login callback failed');
      }
    };

    handleCallback();
  }, []);

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-6 max-w-md">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0" />
            <div>
              <h2 className="text-red-400 font-medium">Login Failed</h2>
              <p className="text-red-300/80 text-sm mt-1">{error}</p>
              <a
                href="/"
                className="inline-block mt-4 text-sm text-blue-400 hover:text-blue-300"
              >
                Return to login
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  }

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
        <p className="text-slate-400">Completing sign in...</p>
      </div>
    </div>
  );
}
