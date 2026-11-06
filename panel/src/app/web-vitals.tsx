'use client'
import { useReportWebVitals } from 'next/web-vitals'

// Progi zgodne z Google Core Web Vitals 2025
const THRESHOLDS = {
  LCP:  { good: 2500, poor: 4000 },
  INP:  { good: 200,  poor: 500  },
  CLS:  { good: 0.1,  poor: 0.25 },
  FCP:  { good: 1800, poor: 3000 },
  TTFB: { good: 800,  poor: 1800 },
}

function rating(name: string, value: number): 'good' | 'needs-improvement' | 'poor' {
  const t = THRESHOLDS[name as keyof typeof THRESHOLDS]
  if (!t) return 'good'
  if (value <= t.good) return 'good'
  if (value <= t.poor) return 'needs-improvement'
  return 'poor'
}

export function WebVitals() {
  useReportWebVitals(({ name, value, id }) => {
    const r = rating(name, value)
    if (r === 'poor') {
      console.warn(`[WebVitals] ${name} POOR: ${Math.round(value)}ms (id=${id})`)
    } else if (process.env.NODE_ENV === 'development') {
      console.log(`[WebVitals] ${name} ${r}: ${Math.round(value)}${name === 'CLS' ? '' : 'ms'}`)
    }
    // TODO: wysyłaj do /v1/vitals albo zewnętrznego analytics kiedy będzie endpoint
  })
  return null
}
