'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { register } from '@/lib/api'

export default function RegisterPage() {
  const router = useRouter()
  const [form, setForm] = useState({ name: '', email: '', password: '', facility_name: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [rawKey, setRawKey] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await register(form.name, form.email, form.password, form.facility_name)
      if (data.api_key?.raw_key) {
        setRawKey(data.api_key.raw_key)
      } else {
        router.push('/scan')
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Błąd rejestracji')
    } finally {
      setLoading(false)
    }
  }

  if (rawKey) {
    return (
      <div className="w-full max-w-sm">
        <div className="bg-white rounded-3xl shadow-sm border border-blue-50 p-8">
          <div className="w-12 h-12 rounded-2xl mx-auto mb-4 flex items-center justify-center"
               style={{ background: '#E0F2FE' }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path d="M9 12l2 2 4-4M12 3C7.03 3 3 7.03 3 12s4.03 9 9 9 9-4.03 9-9-4.03-9-9-9z"
                stroke="#0284C7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <h2 className="text-lg font-bold text-center mb-1" style={{ color: '#0B1A30' }}>Konto utworzone!</h2>
          <p className="text-xs text-center mb-5" style={{ color: '#64748B' }}>
            Zapisz swój klucz API — wyświetlamy go tylko raz
          </p>

          <div className="rounded-xl p-3 mb-5 border" style={{ background: '#F0F7FF', borderColor: '#BAE6FD' }}>
            <p className="text-[10px] font-semibold mb-1" style={{ color: '#0369A1' }}>TWÓJ KLUCZ API</p>
            <code className="text-xs font-mono break-all" style={{ color: '#0B1A30' }}>{rawKey}</code>
          </div>

          <button
            onClick={() => { navigator.clipboard.writeText(rawKey) }}
            className="w-full py-2 rounded-xl text-sm font-semibold mb-3 border transition-colors"
            style={{ borderColor: '#BAE6FD', color: '#0284C7' }}>
            Kopiuj klucz
          </button>

          <button
            onClick={() => router.push('/scan')}
            className="w-full py-2.5 rounded-xl text-sm font-semibold text-white transition-all hover:shadow-md"
            style={{ background: 'linear-gradient(135deg, #38BDF8, #0284C7)' }}>
            Przejdź do panelu →
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full max-w-sm">
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
        <h1 className="text-xl font-bold mb-1" style={{ color: '#0B1A30' }}>Utwórz konto</h1>
        <p className="text-sm mb-6" style={{ color: '#64748B' }}>Rozpocznij 14-dniowy okres próbny — bez karty</p>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-xl text-sm bg-red-50 border border-red-100 text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold mb-1.5" style={{ color: '#475569' }}>Imię i nazwisko</label>
            <input
              required value={form.name}
              onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
              placeholder="Jan Kowalski"
              className="w-full text-sm border rounded-xl px-3.5 py-2.5 focus:outline-none transition-colors"
              style={{ borderColor: '#BAE6FD' }}
              onFocus={e => e.target.style.borderColor = '#0284C7'}
              onBlur={e => e.target.style.borderColor = '#BAE6FD'}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1.5" style={{ color: '#475569' }}>Nazwa placówki</label>
            <input
              value={form.facility_name}
              onChange={e => setForm(p => ({ ...p, facility_name: e.target.value }))}
              placeholder="Centrum Medyczne XYZ"
              className="w-full text-sm border rounded-xl px-3.5 py-2.5 focus:outline-none transition-colors"
              style={{ borderColor: '#BAE6FD' }}
              onFocus={e => e.target.style.borderColor = '#0284C7'}
              onBlur={e => e.target.style.borderColor = '#BAE6FD'}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1.5" style={{ color: '#475569' }}>Email</label>
            <input
              type="email" required value={form.email}
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
              Hasło <span style={{ color: '#94A3B8', fontWeight: 400 }}>(min. 8 znaków)</span>
            </label>
            <input
              type="password" required minLength={8} value={form.password}
              onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
              placeholder="••••••••"
              className="w-full text-sm border rounded-xl px-3.5 py-2.5 focus:outline-none transition-colors"
              style={{ borderColor: '#BAE6FD' }}
              onFocus={e => e.target.style.borderColor = '#0284C7'}
              onBlur={e => e.target.style.borderColor = '#BAE6FD'}
            />
          </div>

          <button
            type="submit" disabled={loading}
            className="w-full py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-50 transition-all hover:shadow-md"
            style={{ background: 'linear-gradient(135deg, #38BDF8, #0284C7)' }}>
            {loading ? 'Tworzenie konta...' : 'Utwórz konto za darmo'}
          </button>
        </form>

        <p className="mt-5 text-center text-xs" style={{ color: '#94A3B8' }}>
          Masz już konto?{' '}
          <Link href="/login" className="font-semibold" style={{ color: '#0284C7' }}>
            Zaloguj się
          </Link>
        </p>
      </div>
    </div>
  )
}
