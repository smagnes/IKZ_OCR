'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { login } from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const [form, setForm] = useState({ email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(form.email, form.password)
      router.push('/scan')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Błąd logowania')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-full max-w-sm">
      {/* Logo */}
      <div className="flex items-center gap-3 mb-8 justify-center">
        <div className="w-10 h-10 rounded-2xl flex items-center justify-center"
             style={{ background: 'linear-gradient(135deg, #38BDF8, #0284C7)' }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M9 12h6M12 9v6M12 3C7.03 3 3 7.03 3 12s4.03 9 9 9 9-4.03 9-9-4.03-9-9-9z"
              stroke="white" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>
        <div>
          <p className="text-lg font-bold" style={{ color: '#0B1A30' }}>IKZOCR</p>
          <p className="text-[11px]" style={{ color: '#64748B' }}>Platforma AI dla medycyny</p>
        </div>
      </div>

      <div className="bg-white rounded-3xl shadow-sm border border-blue-50 p-8">
        <h1 className="text-xl font-bold mb-1" style={{ color: '#0B1A30' }}>Zaloguj się</h1>
        <p className="text-sm mb-6" style={{ color: '#64748B' }}>Witaj ponownie w panelu IKZOCR</p>

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
              style={{ borderColor: '#BAE6FD' }}
              onFocus={e => e.target.style.borderColor = '#0284C7'}
              onBlur={e => e.target.style.borderColor = '#BAE6FD'}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1.5" style={{ color: '#475569' }}>
              Hasło
            </label>
            <input
              type="password"
              required
              value={form.password}
              onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
              placeholder="••••••••"
              className="w-full text-sm border rounded-xl px-3.5 py-2.5 focus:outline-none transition-colors"
              style={{ borderColor: '#BAE6FD' }}
              onFocus={e => e.target.style.borderColor = '#0284C7'}
              onBlur={e => e.target.style.borderColor = '#BAE6FD'}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-50 transition-all hover:shadow-md"
            style={{ background: 'linear-gradient(135deg, #38BDF8, #0284C7)' }}>
            {loading ? 'Logowanie...' : 'Zaloguj się'}
          </button>
        </form>

        <p className="mt-5 text-center text-xs" style={{ color: '#94A3B8' }}>
          Nie masz konta?{' '}
          <Link href="/register" className="font-semibold" style={{ color: '#0284C7' }}>
            Zarejestruj się
          </Link>
        </p>
      </div>

      <p className="mt-6 text-center text-[11px]" style={{ color: '#CBD5E1' }}>
        © 2026 IKZOCR · kontakt@ikzocr.pl
      </p>
    </div>
  )
}
