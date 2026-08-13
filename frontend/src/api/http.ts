export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
let authToken = ''

export function setAuthToken(token: string) {
  authToken = token
}

export class HttpError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message)
    this.name = 'HttpError'
  }
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...init.headers,
    },
  })

  if (!response.ok) {
    const body = await response.text()
    let message = body || `Request failed (${response.status})`
    try {
      const parsed = JSON.parse(body) as { detail?: string }
      message = parsed.detail || message
    } catch {
      // Keep the response body when the server did not return JSON.
    }
    throw new HttpError(message, response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}
