'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import clsx from 'clsx'
import { getUser, logout } from '@/lib/auth'
import { fetchMe } from '@/lib/api'

const NAV = [
  { href: '/scan',       icon: ScanIcon,  label: 'Skanowanie' },
  { href: '/documents',  icon: DocIcon,   label: 'Dokumenty' },
  { href: '/statistics', icon: ChartIcon, label: 'Statystyki' },
]
const NAV2 = [
  { href: '/api-keys',   icon: KeyIcon,      label: 'API / IKZ Mobile' },
  { href: '/facilities', icon: HospitalIcon, label: 'Placówki' },
  { href: '/plan',       icon: PlanIcon,     label: 'Mój Plan' },
]

export default function Sidebar() {
  const path = usePathname()
  const router = useRouter()
  const [planInfo, setPlanInfo] = useState({ plan: 'starter', used: 0, limit: 200 })
  const user = getUser()

  useEffect(() => {
    fetchMe()
      .then(d => setPlanInfo({ plan: d.plan, used: d.scans_this_month, limit: d.scans_limit }))
      .catch(() => {
        const u = getUser()
        if (u) setPlanInfo({ plan: u.plan ?? 'starter', used: u.scans_this_month ?? 0, limit: u.scans_limit ?? 200 })
      })
  }, [])

  const pct = Math.min(100, Math.round((planInfo.used / planInfo.limit) * 100))

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <aside className="w-56 flex-shrink-0 flex flex-col h-full" style={{ background: '#0B1A30' }}>

      {/* Logo */}
      <div className="px-5 py-5 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
               style={{ background: 'linear-gradient(135deg, #38BDF8, #0284C7)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M9 12h6M12 9v6M12 3C7.03 3 3 7.03 3 12s4.03 9 9 9 9-4.03 9-9-4.03-9-9-9z"
                stroke="white" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-white leading-tight">IKZOCR</p>
            <p className="text-[10px] leading-tight" style={{ color: '#7DD3FC' }}>Platforma AI</p>
          </div>
        </div>
      </div>

      {/* User info */}
      {user && (
        <div className="px-4 py-3 border-b border-white/5">
          <p className="text-xs font-medium text-white truncate">{user.name}</p>
          <p className="text-[10px] truncate" style={{ color: '#64748B' }}>{user.email}</p>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 p-3 overflow-y-auto space-y-0.5">
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = path.startsWith(href)
          return (
            <Link key={href} href={href}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all',
                active ? 'text-white font-medium' : 'text-blue-200/60 hover:text-blue-100 hover:bg-white/5'
              )}
              style={active ? { background: 'rgba(56,189,248,0.18)' } : {}}>
              <Icon active={active} />
              {label}
            </Link>
          )
        })}

        <p className="text-[10px] uppercase tracking-widest px-3 pt-5 pb-1.5 font-medium"
           style={{ color: '#38BDF8', opacity: 0.6 }}>
          Integracje
        </p>

        {NAV2.map(({ href, icon: Icon, label }) => {
          const active = path.startsWith(href)
          return (
            <Link key={href} href={href}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all',
                active ? 'text-white font-medium' : 'text-blue-200/60 hover:text-blue-100 hover:bg-white/5'
              )}
              style={active ? { background: 'rgba(56,189,248,0.18)' } : {}}>
              <Icon active={active} />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Plan widget */}
      <div className="p-3 border-t border-white/10 space-y-2">
        <Link href="/plan">
          <div className="px-3 py-2.5 rounded-xl cursor-pointer hover:opacity-90 transition-opacity"
               style={{ background: 'rgba(2,132,199,0.2)' }}>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-medium capitalize" style={{ color: '#7DD3FC' }}>
                Plan {planInfo.plan}
              </span>
              <span className="text-[10px]" style={{ color: '#38BDF8' }}>
                {planInfo.used} / {planInfo.limit}
              </span>
            </div>
            <div className="h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.1)' }}>
              <div className="h-full rounded-full transition-all"
                   style={{ width: `${pct}%`, background: 'linear-gradient(90deg, #38BDF8, #0284C7)' }} />
            </div>
          </div>
        </Link>

        <div className="flex items-center justify-between px-3 py-1.5">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: '#38BDF8' }} />
            <span className="text-[11px]" style={{ color: '#7DD3FC' }}>IKZ Mobile</span>
          </div>
          <button onClick={handleLogout}
            className="text-[10px] px-2 py-0.5 rounded-lg transition-colors hover:bg-white/10"
            style={{ color: '#475569' }}>
            Wyloguj
          </button>
        </div>
      </div>
    </aside>
  )
}

function ScanIcon({ active }: { active: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ color: active ? '#38BDF8' : 'currentColor' }}>
      <path d="M3 7V5a2 2 0 012-2h2M17 3h2a2 2 0 012 2v2M21 17v2a2 2 0 01-2 2h-2M7 21H5a2 2 0 01-2-2v-2"
        stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
      <rect x="8" y="8" width="8" height="8" rx="1" stroke="currentColor" strokeWidth="1.8"/>
    </svg>
  )
}
function DocIcon({ active }: { active: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ color: active ? '#38BDF8' : 'currentColor' }}>
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z"
        stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"
        stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
    </svg>
  )
}
function ChartIcon({ active }: { active: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ color: active ? '#38BDF8' : 'currentColor' }}>
      <path d="M18 20V10M12 20V4M6 20v-6"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}
function KeyIcon({ active }: { active: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ color: active ? '#38BDF8' : 'currentColor' }}>
      <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"
        stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}
function HospitalIcon({ active }: { active: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ color: active ? '#38BDF8' : 'currentColor' }}>
      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"
        stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M9 22V12h6v10M12 7v4M10 9h4"
        stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
    </svg>
  )
}
function PlanIcon({ active }: { active: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ color: active ? '#38BDF8' : 'currentColor' }}>
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
        stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}
