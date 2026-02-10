import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import { AuthProvider } from './components/AuthProvider.tsx'
import { RoleProvider } from './contexts/RoleContext.tsx'
import { ErrorBoundary } from './components/ErrorBoundary.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <RoleProvider>
          <App />
        </RoleProvider>
      </AuthProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)

