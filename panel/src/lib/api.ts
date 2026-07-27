import { getToken, setAuth, AuthUser } from './auth'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const DEMO_KEY = process.env.NEXT_PUBLIC_API_KEY ?? 'mk_prod_demo123'

function apiKeyHeaders(extra: Record<string, string> = {}) {
  const key = (typeof window !== 'undefined' && localStorage.getItem('ikzocr_api_key')) || DEMO_KEY
  return { Authorization: `Bearer ${key}`, ...extra }
}

function jwtHeaders(extra: Record<string, string> = {}) {
  const token = getToken()
  return { Authorization: `Bearer ${token}`, ...extra }
}

// ── AUTH ──────────────────────────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<{ token: string; user: AuthUser }> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Błąd logowania' }))
    throw new Error(err.detail ?? 'Błąd logowania')
  }
  const data = await res.json()
  setAuth(data.token, data.user)
  return data
}

export async function register(name: string, email: string, password: string, facility_name?: string) {
  const res = await fetch(`${BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password, facility_name }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Błąd rejestracji' }))
    throw new Error(err.detail ?? 'Błąd rejestracji')
  }
  const data = await res.json()
  if (data.api_key?.raw_key) {
    localStorage.setItem('ikzocr_api_key', data.api_key.raw_key)
  }
  setAuth(data.token, data.user)
  return data
}

export async function fetchMe() {
  const res = await fetch(`${BASE}/auth/me`, { headers: jwtHeaders() })
  if (!res.ok) throw new Error('Błąd pobierania profilu')
  return res.json()
}

// ── OCR / DOCUMENTS ───────────────────────────────────────────────────────────

export async function scanDocument(file: File, silosId?: string): Promise<ScanResult> {
  const form = new FormData()
  form.append('file', file)
  const h = apiKeyHeaders(silosId ? { 'X-IKZ-Silos-Id': silosId } : {})
  const res = await fetch(`${BASE}/v1/scan`, { method: 'POST', headers: h, body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function fetchDocument(scanId: string): Promise<ScanResult> {
  const res = await fetch(`${BASE}/v1/documents/${scanId}`, { headers: apiKeyHeaders() })
  if (!res.ok) throw new Error(await res.text())
  const d = await res.json()
  // Map DB record → ScanResult shape
  return {
    scan_id:           d.id ?? d.scan_id,
    status:            'ok',
    doc_type:          d.doc_type,
    doc_type_label:    d.doc_type_label,
    confidence: {
      text:    d.confidence_overall ?? 0,
      values:  d.confidence_overall ?? 0,
      units:   d.confidence_overall ?? 0,
      overall: d.confidence_overall ?? 0,
    },
    patient:           d.patient ?? null,
    pesel_masked:      d.pesel_masked ?? null,
    doctor:            d.doctor ?? null,
    facility:          d.facility ?? null,
    exam_date:         d.exam_date ?? null,
    fields:            typeof d.fields === 'string' ? JSON.parse(d.fields) : (d.fields ?? {}),
    alerts:            typeof d.alerts === 'string' ? JSON.parse(d.alerts) : (d.alerts ?? []),
    raw_text:          d.raw_text ?? '',
    processing_time_ms: d.processing_time_ms ?? 0,
    ikz_examination_id: d.ikz_examination_id ?? null,
  }
}

export async function deleteDocument(scanId: string): Promise<void> {
  const res = await fetch(`${BASE}/v1/documents/${scanId}`, {
    method: 'DELETE',
    headers: apiKeyHeaders(),
  })
  if (!res.ok) throw new Error(await res.text())
}

export async function fetchDocuments(params?: { doc_type?: string; page?: number }) {
  const qs = new URLSearchParams()
  if (params?.doc_type) qs.set('doc_type', params.doc_type)
  if (params?.page)     qs.set('page', String(params.page))
  const res = await fetch(`${BASE}/v1/documents?${qs}`, { headers: apiKeyHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function fetchStats(): Promise<Stats> {
  const res = await fetch(`${BASE}/v1/stats`, { headers: apiKeyHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function fetchApiKeys() {
  const res = await fetch(`${BASE}/v1/api-keys`, { headers: apiKeyHeaders() })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function exportDocumentsCsv() {
  const res = await fetch(`${BASE}/v1/documents/export`, { headers: apiKeyHeaders() })
  if (!res.ok) throw new Error('Błąd eksportu')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `ikzocr_export_${new Date().toISOString().slice(0,10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

async function _downloadScan(scanId: string, ext: 'txt' | 'md' | 'csv') {
  const res = await fetch(`${BASE}/v1/documents/${scanId}/export.${ext}`, { headers: apiKeyHeaders() })
  if (!res.ok) throw new Error(`Błąd pobierania .${ext}`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `ikzocr_${scanId.slice(0, 8)}.${ext}`
  a.click()
  URL.revokeObjectURL(url)
}

export const downloadScanTxt = (scanId: string) => _downloadScan(scanId, 'txt')
export const downloadScanMd  = (scanId: string) => _downloadScan(scanId, 'md')
export const downloadScanCsv = (scanId: string) => _downloadScan(scanId, 'csv')

export async function setWebhookUrl(keyId: string, webhookUrl: string) {
  const res = await fetch(`${BASE}/v1/api-keys/${keyId}/webhook`, {
    method: 'PATCH',
    headers: { ...apiKeyHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ webhook_url: webhookUrl || null }),
  })
  if (!res.ok) throw new Error('Błąd ustawiania webhooka')
  return res.json()
}

export async function sendScanEmail(scanId: string, to: string) {
  const res = await fetch(`${BASE}/v1/documents/send-email`, {
    method: 'POST',
    headers: { ...apiKeyHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ scan_id: scanId, to }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Błąd wysyłki' }))
    throw new Error(err.detail)
  }
  return res.json()
}

export async function createApiKey(name: string, facility_name: string) {
  const res = await fetch(`${BASE}/v1/api-keys`, {
    method: 'POST',
    headers: { ...apiKeyHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, facility_name }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ── TYPES ─────────────────────────────────────────────────────────────────────

export interface ScanResult {
  scan_id: string
  status: string
  doc_type: string
  doc_type_label: string
  confidence: { text: number; values: number; units: number; overall: number }
  patient?: string
  pesel_masked?: string
  doctor?: string
  facility?: string
  exam_date?: string
  fields: Record<string, string | string[]>
  alerts: string[]
  raw_text: string
  processing_time_ms: number
  ikz_examination_id?: number
}

export interface Stats {
  total_scans: number
  scans_this_month: number
  accuracy: number
  avg_processing_ms: number
  by_type: Record<string, number>
  by_source: Record<string, number>
  monthly_revenue: number
}
