/**
 * UserRoleManager — Admin-only settings page for managing user roles.
 *
 * Displays all users who have logged in via Okta SSO with their current role.
 * Admin can promote/demote users via dropdown (admin / ma / user).
 *
 * Only accessible when:
 *   1. Supabase mode is enabled (VITE_USE_SUPABASE=true)
 *   2. Current user has admin role
 */

import { useState, useEffect } from 'react'
import { Users, Shield, ShieldCheck, Eye, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react'
import { listUsersWithRoles, setUserRole, isSupabaseMode } from '../services/apiRouter'
import { useRole } from '../contexts/RoleContext'

interface UserWithRole {
  user_id: string
  email: string
  role: string
  last_sign_in_at: string | null
  created_at: string | null
}

const ROLE_LABELS: Record<string, { label: string; color: string; icon: typeof Shield }> = {
  admin: { label: 'Admin', color: 'text-red-700 bg-red-50 border-red-200', icon: ShieldCheck },
  ma: { label: 'Medical Associate', color: 'text-blue-700 bg-blue-50 border-blue-200', icon: Shield },
  user: { label: 'Read-Only', color: 'text-slate-600 bg-slate-50 border-slate-200', icon: Eye },
}

export default function UserRoleManager() {
  const { isAdmin } = useRole()
  const [users, setUsers] = useState<UserWithRole[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [savingUserId, setSavingUserId] = useState<string | null>(null)
  const [successUserId, setSuccessUserId] = useState<string | null>(null)

  const fetchUsers = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listUsersWithRoles()
      setUsers(data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isSupabaseMode && isAdmin) {
      fetchUsers()
    }
  }, [isAdmin])

  const handleRoleChange = async (userId: string, newRole: string) => {
    setSavingUserId(userId)
    setError(null)
    try {
      await setUserRole(userId, newRole)
      setUsers(prev => prev.map(u =>
        u.user_id === userId ? { ...u, role: newRole } : u
      ))
      setSuccessUserId(userId)
      setTimeout(() => setSuccessUserId(null), 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update role')
    } finally {
      setSavingUserId(null)
    }
  }

  if (!isSupabaseMode) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-8 text-center">
        <AlertCircle className="w-12 h-12 text-slate-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-slate-700 mb-2">User Management Not Available</h3>
        <p className="text-slate-500">
          User role management requires Supabase mode. In local development, all users have admin access.
        </p>
      </div>
    )
  }

  if (!isAdmin) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-8 text-center">
        <Shield className="w-12 h-12 text-slate-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-slate-700 mb-2">Admin Access Required</h3>
        <p className="text-slate-500">
          Only administrators can manage user roles.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Users className="w-6 h-6 text-primary-500" />
              User Role Management
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Assign roles to control access. Changes take effect on next page load.
            </p>
          </div>
          <button
            onClick={fetchUsers}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Role legend */}
        <div className="flex gap-4 mt-4 flex-wrap">
          {Object.entries(ROLE_LABELS).map(([key, { label, color, icon: Icon }]) => (
            <div key={key} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${color} text-sm`}>
              <Icon className="w-4 h-4" />
              <span className="font-medium">{label}</span>
              <span className="text-xs opacity-70">
                {key === 'admin' ? 'Full access + user management' :
                 key === 'ma' ? 'Full write access' : 'Read-only access'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <span className="text-red-700">{error}</span>
        </div>
      )}

      {/* Users table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center">
            <RefreshCw className="w-8 h-8 text-slate-400 animate-spin mx-auto mb-3" />
            <p className="text-slate-500">Loading users...</p>
          </div>
        ) : users.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500">No users found. Users will appear here after they log in via Okta SSO.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">User</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Role</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Last Login</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users.map((user) => {
                const roleInfo = ROLE_LABELS[user.role] || ROLE_LABELS.user
                const isSaving = savingUserId === user.user_id
                const showSuccess = successUserId === user.user_id

                return (
                  <tr key={user.user_id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-slate-900">{user.email}</div>
                      <div className="text-xs text-slate-400 font-mono">{user.user_id.slice(0, 8)}...</div>
                    </td>
                    <td className="px-6 py-4">
                      <select
                        value={user.role}
                        onChange={(e) => handleRoleChange(user.user_id, e.target.value)}
                        disabled={isSaving}
                        className={`px-3 py-1.5 rounded-lg border text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary-500/20 ${roleInfo.color} ${isSaving ? 'opacity-50 cursor-wait' : 'cursor-pointer'}`}
                      >
                        <option value="admin">Admin</option>
                        <option value="ma">Medical Associate</option>
                        <option value="user">Read-Only</option>
                      </select>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-500">
                      {user.last_sign_in_at
                        ? new Date(user.last_sign_in_at).toLocaleDateString('en-US', {
                            month: 'short', day: 'numeric', year: 'numeric',
                            hour: 'numeric', minute: '2-digit'
                          })
                        : 'Never'}
                    </td>
                    <td className="px-6 py-4">
                      {isSaving ? (
                        <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />
                      ) : showSuccess ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : null}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
