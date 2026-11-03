const TOKEN_KEY = 'ikzocr_token'
const USER_KEY  = 'ikzocr_user'
// Klucz API sesji demo trzymamy osobno, żeby nie nadpisać klucza zwykłego konta
export const DEMO_API_KEY = 'ikzocr_demo_api_key'

export interface AuthUser {
  id: string
  name: string
  email: string
  plan?: string
  scans_limit?: number
  scans_this_month?: number
  is_demo?: boolean
  expires_at?: string
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

export function getUser(): AuthUser | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function setAuth(token: string, user: AuthUser) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function isAuthenticated(): boolean {
  const token = getToken()
  if (!token) return false
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 > Date.now()
  } catch {
    return false
  }
}

export function isDemo(): boolean {
  return !!getUser()?.is_demo
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem(DEMO_API_KEY)
}
