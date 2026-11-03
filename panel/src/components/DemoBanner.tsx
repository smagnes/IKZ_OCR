'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getUser, logout } from '@/lib/auth'
import { endDemo } from '@/lib/api'

function remaining(expiresAt?: string): string {
  if (!expiresAt) return ''
  const ms = new Date(expiresAt).getTime() - Date.now()
  if (ms <= 0) return 'wygasła'
  const h = Math.floor(ms / 3_600_000)
  const m = Math.floor((ms % 3_600_000) / 60_000)
  return h > 0 ? `${h} h ${m} min` : `${m} min`
}

export default function DemoBanner() {
  const router = useRouter()
  const user = getUser()
  const [left, setLeft] = useState(remaining(user?.expires_at))

  useEffect(() => {
    const tick = () => {
      const r = remaining(user?.expires_at)
      setLeft(r)
      if (r === 'wygasła') {
        logout()
        router.push('/login')
      }
    }
    tick()
    const id = setInterval(tick, 30_000)
    return () => clearInterval(id)
  }, [user?.expires_at, router])

  const finish = async () => {
    await endDemo()
    logout()
    router.push('/login')
  }

  return (
    <div role="alert"
         className="flex flex-wrap items-center justify-between gap-2 px-6 py-2.5 text-xs border-b"
         style={{ background: '#FFF7ED', borderColor: '#FED7AA', color: '#9A3412' }}>
      <p>
        <strong>Wersja demo — nie wgrywaj dokumentów z danymi pacjentów.</strong>{' '}
        Sesja jest prywatna, limit {user?.scans_limit ?? 10} skanów, dane zostaną usunięte
        {left ? ` za ${left}` : ' po 24 h'}. Wysyłka email i do IKZ Mobile jest wyłączona.
      </p>
      <button onClick={finish}
        className="px-3 py-1 rounded-lg border font-semibold bg-white hover:bg-orange-50"
        style={{ borderColor: '#FED7AA' }}>
        Zakończ demo i usuń dane
      </button>
    </div>
  )
}
