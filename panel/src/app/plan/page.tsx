'use client'
import { useState, useEffect } from 'react'
import { fetchMe } from '@/lib/api'
import { getUser, logout } from '@/lib/auth'
import { useRouter } from 'next/navigation'

const PLANS = [
  {
    name: 'Starter',
    price: '€49',
    scans: '200 scans / month',
    features: ['API access', 'Web panel', 'Email support'],
    color: '#D6F5EC',
    textColor: '#007A57',
    current: (plan: string) => plan === 'starter',
  },
  {
    name: 'Pro',
    price: '€119',
    scans: '1,000 scans / month',
    features: ['Everything in Starter', 'Webhook', 'CSV export', 'Priority support'],
    color: '#00B37E',
    textColor: 'white',
    current: (plan: string) => plan === 'pro',
  },
  {
    name: 'Enterprise',
    price: '€349',
    scans: '5,000 scans / month',
    features: ['Everything in Pro', 'Dedicated account manager', 'SLA 99.9%', 'On-premise option'],
    color: '#0D1F17',
    textColor: 'white',
    current: (plan: string) => plan === 'enterprise',
  },
]

export default function PlanPage() {
  const router = useRouter()
  const [user, setUser] = useState(getUser())
  const [me, setMe] = useState<{
    plan: string; scans_limit: number; scans_this_month: number; created_at: string
  } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMe()
      .then(data => { setMe(data); setUser(u => u ? { ...u, ...data } : data) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const plan = me?.plan ?? user?.plan ?? 'starter'
  const used = me?.scans_this_month ?? user?.scans_this_month ?? 0
  const limit = me?.scans_limit ?? user?.scans_limit ?? 200
  const pct = Math.min(100, Math.round((used / limit) * 100))
  const barColor = pct >= 90 ? '#EF4444' : pct >= 70 ? '#F59E0B' : '#00B37E'

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-6 py-3.5 bg-white border-b border-blue-100/60">
        <div>
          <h1 className="text-sm font-semibold" style={{ color: '#0D1F17' }}>My Plan</h1>
          <p className="text-[11px] text-slate-400">Manage your subscription and account</p>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6 space-y-5 max-w-3xl">

        {/* Account card */}
        <div className="bg-white border border-blue-50 rounded-2xl p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 text-lg font-bold text-white"
               style={{ background: 'linear-gradient(135deg, #00E5A0, #00B37E)' }}>
            {(user?.name ?? 'U')[0].toUpperCase()}
          </div>
          <div className="flex-1">
            <p className="text-sm font-semibold" style={{ color: '#0D1F17' }}>{user?.name ?? '—'}</p>
            <p className="text-xs" style={{ color: '#64748B' }}>{user?.email ?? '—'}</p>
            {me?.created_at && (
              <p className="text-[11px] mt-0.5" style={{ color: '#94A3B8' }}>
                Member since: {new Date(me.created_at).toLocaleDateString('en-GB')}
              </p>
            )}
          </div>
          <button
            onClick={handleLogout}
            className="text-xs px-3 py-1.5 rounded-xl border transition-colors hover:bg-red-50 hover:border-red-200 hover:text-red-600"
            style={{ borderColor: '#E2E8F0', color: '#94A3B8' }}>
            Sign out
          </button>
        </div>

        {/* Usage card */}
        <div className="bg-white border border-blue-50 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: '#007A57' }}>
              Usage this month
            </p>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full capitalize"
                  style={{ background: '#D6F5EC', color: '#00B37E' }}>
              Plan {plan}
            </span>
          </div>

          {loading ? (
            <div className="flex items-center gap-2 text-sm" style={{ color: '#00B37E' }}>
              <div className="w-4 h-4 border-2 rounded-full animate-spin"
                   style={{ borderColor: '#00B37E', borderTopColor: 'transparent' }} />
              Loading...
            </div>
          ) : (
            <>
              <div className="flex items-end justify-between mb-2">
                <span className="text-3xl font-bold" style={{ color: '#0D1F17' }}>{used}</span>
                <span className="text-sm" style={{ color: '#94A3B8' }}>/ {limit} scans</span>
              </div>
              <div className="h-2.5 rounded-full overflow-hidden" style={{ background: '#D6F5EC' }}>
                <div className="h-full rounded-full transition-all"
                     style={{ width: `${pct}%`, background: barColor }} />
              </div>
              <p className="text-[11px] mt-2" style={{ color: '#94A3B8' }}>
                {pct}% used · {limit - used} scans remaining
              </p>
            </>
          )}
        </div>

        {/* Plans */}
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest mb-3" style={{ color: '#007A57' }}>
            Available plans
          </p>
          <div className="grid grid-cols-3 gap-3">
            {PLANS.map(p => {
              const isCurrent = p.current(plan)
              return (
                <div key={p.name}
                     className="rounded-2xl p-5 border-2 relative transition-all"
                     style={{
                       borderColor: isCurrent ? p.color === '#D6F5EC' ? '#00B37E' : p.color : '#D6F5EC',
                       background: p.color,
                     }}>
                  {isCurrent && (
                    <span className="absolute top-3 right-3 text-[10px] font-bold px-2 py-0.5 rounded-full"
                          style={{ background: 'rgba(255,255,255,0.25)', color: p.textColor }}>
                      Active
                    </span>
                  )}
                  <p className="text-base font-bold mb-0.5" style={{ color: p.textColor }}>{p.name}</p>
                  <p className="text-xl font-bold mb-0.5" style={{ color: p.textColor }}>{p.price}</p>
                  <p className="text-[11px] mb-4 opacity-70" style={{ color: p.textColor }}>/ month, net</p>
                  <p className="text-xs font-semibold mb-3 opacity-80" style={{ color: p.textColor }}>{p.scans}</p>
                  <ul className="space-y-1.5 mb-5">
                    {p.features.map(f => (
                      <li key={f} className="flex items-center gap-1.5 text-[11px]" style={{ color: p.textColor, opacity: 0.85 }}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                          <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                        </svg>
                        {f}
                      </li>
                    ))}
                  </ul>
                  {!isCurrent && (
                    <button
                      onClick={() => alert('Contact us: kontakt@ikzocr.pl')}
                      className="w-full py-2 rounded-xl text-xs font-semibold transition-all hover:opacity-90"
                      style={{
                        background: p.color === '#D6F5EC' ? '#00B37E' : 'rgba(255,255,255,0.2)',
                        color: p.color === '#D6F5EC' ? 'white' : p.textColor,
                        border: '1px solid rgba(255,255,255,0.3)',
                      }}>
                      Upgrade
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Contact */}
        <div className="rounded-2xl p-4 border" style={{ background: '#F5F8F6', borderColor: '#B3EDD8' }}>
          <p className="text-xs font-semibold mb-1" style={{ color: '#007A57' }}>Questions about your plan or invoice?</p>
          <p className="text-xs" style={{ color: '#64748B' }}>
            Write to <a href="mailto:kontakt@ikzocr.pl" className="font-medium" style={{ color: '#00B37E' }}>kontakt@ikzocr.pl</a>
            {' '}— we respond within 24h on business days.
          </p>
        </div>
      </div>
    </div>
  )
}
