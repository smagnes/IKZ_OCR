'use client'
import { useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import Sidebar from './Sidebar'
import { isAuthenticated } from '@/lib/auth'

const AUTH_ROUTES = ['/login', '/register']

export default function ConditionalLayout({ children }: { children: React.ReactNode }) {
  const path = usePathname()
  const router = useRouter()
  const isAuthPage = AUTH_ROUTES.includes(path)
  const [checking, setChecking] = useState(!isAuthPage)

  useEffect(() => {
    if (!isAuthPage && !isAuthenticated()) {
      router.push('/login')
    } else {
      setChecking(false)
    }
  }, [path, isAuthPage, router])

  if (isAuthPage) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#F5F8F6' }}>
        {children}
      </div>
    )
  }

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#F5F8F6' }}>
        <div className="w-6 h-6 border-2 rounded-full animate-spin"
             style={{ borderColor: '#00B37E', borderTopColor: 'transparent' }} />
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#F5F8F6' }}>
      <Sidebar />
      <main className="flex-1 overflow-hidden flex flex-col">
        {children}
      </main>
    </div>
  )
}
