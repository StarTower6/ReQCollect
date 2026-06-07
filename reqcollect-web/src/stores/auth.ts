/* ── Auth Store ── */

import { defineStore } from 'pinia'
import { apiPost, apiGet, apiPatch } from '@/api/client'
import router from '@/router'

export interface UserInfo {
  id: string
  username: string
  display_name: string
  email: string
  department: string
  role: string
  source: string
  is_active: boolean
  created_at: string
  updated_at: string
}

const TOKEN_KEY = 'reqcollect_token'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || null,
    user: null as UserInfo | null,
    loading: false,
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
    isAdmin: (state) => state.user?.role === 'admin',
  },

  actions: {
    async login(username: string, password: string) {
      this.loading = true
      try {
        const res: any = await apiPost('/auth/login', { username, password })
        this.token = res.access_token
        this.user = res.user
        localStorage.setItem(TOKEN_KEY, this.token!)
        return true
      } catch (e: any) {
        this.token = null
        this.user = null
        throw e
      } finally {
        this.loading = false
      }
    },

    async loadUser() {
      if (!this.token) return
      try {
        const res: any = await apiGet('/auth/me')
        this.user = res.user
      } catch {
        this.logout()
      }
    },

    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      router.push('/login')
    },
  },
})
