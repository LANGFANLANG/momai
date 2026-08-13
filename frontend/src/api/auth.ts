import { request } from './http'
import type { AuthCredentials, AuthSession, CaptchaChallenge, User } from '@/types/auth'

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
})

export const authApi = {
  login: (payload: AuthCredentials) => request<AuthSession>('/api/auth/login', json('POST', payload)),
  register: (payload: AuthCredentials) => request<AuthSession>('/api/auth/register', json('POST', payload)),
  captcha: () => request<CaptchaChallenge>('/api/auth/captcha'),
  me: () => request<User>('/api/auth/me'),
}
