'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { login } from '@/lib/api'
import { setAuth } from '@/lib/auth'

export default function LoginPage() {
  const router = useRouter()
  const [form, setForm] = useState({ email: '', password: '' })
  const [loading, setLoading] = useState(false)

  const demoLogin = () => {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).replace(/=/g, '')
    const payload = btoa(JSON.stringify({
      sub: 'demo', email: 'demo@ikzocr.pl', name: 'Demo User',
      exp: Math.floor(Date.now() / 1000) + 86400 * 30,
    })).replace(/=/g, '')
    const fakeJwt = `${header}.${payload}.demo`
    setAuth(fakeJwt, { id: 'demo', name: 'Demo User', email: 'demo@ikzocr.pl', plan: 'pro', scans_limit: 500, scans_this_month: 12 })
    router.push('/scan')
  }
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(form.email, form.password)
      router.push('/scan')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-full max-w-sm">
      {/* Logo */}
      <div className="flex items-center gap-3 mb-8 justify-center">
        <div className="w-10 h-10 rounded-2xl flex items-center justify-center"
             style={{ background: 'linear-gradient(135deg, #00E5A0, #00B37E)' }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M9 12h6M12 9v6M12 3C7.03 3 3 7.03 3 12s4.03 9 9 9 9-4.03 9-9-4.03-9-9-9z"
              stroke="white" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>
        <div>
          <p className="text-lg font-bold" style={{ color: '#0D1F17' }}>IKZOCR</p>
          <p className="text-[11px]" style={{ color: '#64748B' }}>AI Platform for Medicine</p>
        </div>
      </div>

      <div className="bg-white rounded-3xl shadow-sm border border-blue-50 p-8">
        <h1 className="text-xl font-bold mb-1" style={{ color: '#0D1F17' }}>Sign in</h1>
        <p className="text-sm mb-6" style={{ color: '#64748B' }}>Welcome back to IKZOCR</p>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-xl text-sm bg-red-50 border border-red-100 text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold mb-1.5" style={{ color: '#475569' }}>
              Email
            </label>
            <input
              type="email"
              required
              value={form.email}
              onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
              placeholder="jan@placowka.pl"
              className="w-full text-sm border rounded-xl px-3.5 py-2.5 focus:outline-none transition-colors"
              style={{ borderColor: '#B3EDD8' }}
              onFocus={e => e.target.style.borderColor = '#00B37E'}
              onBlur={e => e.target.style.borderColor = '#B3EDD8'}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1.5" style={{ color: '#475569' }}>
              Password
            </label>
            <input
              type="password"
              required
              value={form.password}
              onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
              placeholder="••••••••"
              className="w-full text-sm border rounded-xl px-3.5 py-2.5 focus:outline-none transition-colors"
              style={{ borderColor: '#B3EDD8' }}
              onFocus={e => e.target.style.borderColor = '#00B37E'}
              onBlur={e => e.target.style.borderColor = '#B3EDD8'}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-50 transition-all hover:shadow-md"
            style={{ background: 'linear-gradient(135deg, #00E5A0, #00B37E)' }}>
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="mt-4 pt-4 border-t border-blue-50">
          <button
            type="button"
            onClick={demoLogin}
            className="w-full py-2.5 rounded-xl text-sm font-semibold transition-all hover:opacity-90 border"
            style={{ background: '#F5F8F6', color: '#007A57', borderColor: '#B3EDD8' }}>
            Try Demo (no login required)
          </button>
        </div>

        <p className="mt-4 text-center text-xs" style={{ color: '#94A3B8' }}>
          Don&apos;t have an account?{' '}
          <Link href="/register" className="font-semibold" style={{ color: '#00B37E' }}>
            Register
          </Link>
        </p>
      </div>

      <p className="mt-6 text-center text-[11px]" style={{ color: '#CBD5E1' }}>
        © 2026 IKZOCR · kontakt@ikzocr.pl
      </p>
    </div>
  )
}
