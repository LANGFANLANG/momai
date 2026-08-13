import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api/auth'
import { setAuthToken } from '@/api/http'
import type { AuthCredentials, User } from '@/types/auth'

const TOKEN_KEY = 'paper-agent-auth-token'
const USER_KEY = 'paper-agent-auth-user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const user = ref<User | null>(JSON.parse(localStorage.getItem(USER_KEY) || 'null') as User | null)
  const loading = ref(false)

  setAuthToken(token.value)

  function persist(nextToken: string, nextUser: User) {
    token.value = nextToken
    user.value = nextUser
    localStorage.setItem(TOKEN_KEY, nextToken)
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser))
    setAuthToken(nextToken)
  }

  async function login(payload: AuthCredentials) {
    loading.value = true
    try {
      const session = await authApi.login(payload)
      persist(session.token, session.user)
      return session.user
    } finally {
      loading.value = false
    }
  }

  async function register(payload: AuthCredentials) {
    loading.value = true
    try {
      const session = await authApi.register(payload)
      persist(session.token, session.user)
      return session.user
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setAuthToken('')
  }

  return { token, user, loading, login, register, logout }
})
