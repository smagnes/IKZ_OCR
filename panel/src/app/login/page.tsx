'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { login, startDemo } from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const [form, setForm] = useState({ email: '', password: '' })
  const [loading, setLoading] = useState(false)

  const [demoLoading, setDemoLoading] = useState(false)
  const [error, setError] = useState('')

  // Każde kliknięcie tworzy osobne, tymczasowe konto demo (24 h, 10 skanów)
  const demoLogin = async () => {
    setError('')
    setDemoLoading(true)
    try {
      await startDemo()
      router.push('/scan')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Nie udało się uruchomić demo')
    } finally {
      setDemoLoading(false)
    }
  }

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
      <div className="flex items-center gap-3 mb-6 justify-center">
        <div className="w-10 h-10 rounded-2xl flex items-center justify-center"
             style={{ background: 'linear-gradient(135deg, #0284C7, #0369A1)' }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M9 12h6M12 9v6M12 3C7.03 3 3 7.03 3 12s4.03 9 9 9 9-4.03 9-9-4.03-9-9-9z"
              stroke="white" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>
        <div>
          <p className="text-lg font-bold" style={{ color: '#0B1C2E' }}>IKZOCR</p>
          <p className="text-[11px]" style={{ color: '#64748B' }}>Platforma AI dla medycyny</p>
        </div>
      </div>

      {/* Demo card */}
      <div className="mb-4 rounded-2xl border p-4" style={{ background: '#EFF6FF', borderColor: '#BFDBFE' }}>
        <p className="text-sm font-semibold mb-1" style={{ color: '#1D4ED8' }}>Wypróbuj bez rejestracji</p>
        <p className="text-xs mb-3" style={{ color: '#475569' }}>Konto demo z pełnym dostępem — OCR, tłumaczenie, dokumenty</p>
        <button
          type="button"
          onClick={demoLogin}
          disabled={demoLoading}
          className="w-full py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-50 transition-all hover:shadow-md"
          style={{ background: 'linear-gradient(135deg, #2563EB, #1D4ED8)' }}>
          {demoLoading ? 'Ładowanie...' : 'Wypróbuj demo →'}
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border p-6" style={{ borderColor: '#E2E8F0' }}>
        <h1 className="text-xl font-bold mb-1" style={{ color: '#0B1C2E' }}>Zaloguj się</h1>
        <p className="text-sm mb-5" style={{ color: '#64748B' }}>Witaj ponownie w panelu IKZOCR</p>

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
              style={{ borderColor: '#CBD5E1' }}
              onFocus={e => e.target.style.borderColor = '#2563EB'}
              onBlur={e => e.target.style.borderColor = '#CBD5E1'}
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
              style={{ borderColor: '#CBD5E1' }}
              onFocus={e => e.target.style.borderColor = '#2563EB'}
              onBlur={e => e.target.style.borderColor = '#CBD5E1'}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-50 transition-all hover:shadow-md"
            style={{ background: 'linear-gradient(135deg, #2563EB, #1D4ED8)' }}>
            {loading ? 'Logowanie...' : 'Zaloguj się'}
          </button>
        </form>

        <p className="mt-4 text-center text-xs" style={{ color: '#94A3B8' }}>
          Nie masz konta?{' '}
          <Link href="/register" className="font-semibold" style={{ color: '#2563EB' }}>
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
