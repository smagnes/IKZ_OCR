'use client'
import { useState, useRef, useCallback } from 'react'
import clsx from 'clsx'
import { getToken } from '@/lib/auth'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

interface TranslateResult {
  original_text: string
  translated_text: string
  document_type: string
  key_findings: { label: string; value: string; flag?: 'high' | 'low' | 'normal' }[]
  clinical_notes: string
  source_language: string
  processing_time_ms: number
}

async function translateDocument(file: File): Promise<TranslateResult> {
  const fd = new FormData()
  fd.append('file', file)
  const token = getToken() ?? ''
  const res = await fetch(`${API_BASE}/translate`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: fd,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Translation failed' }))
    throw new Error(err.detail ?? 'Translation failed')
  }
  return res.json()
}

export default function TranslatePage() {
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [status, setStatus] = useState<'idle' | 'processing' | 'done' | 'error'>('idle')
  const [result, setResult] = useState<TranslateResult | null>(null)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'side' | 'findings'>('side')
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback((f: File) => {
    setFile(f)
    setResult(null)
    setStatus('idle')
    setError('')
  }, [])

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  const run = async () => {
    if (!file) return
    setStatus('processing')
    setError('')
    try {
      const r = await translateDocument(file)
      setResult(r)
      setStatus('done')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Translation error')
      setStatus('error')
    }
  }

  const copy = (text: string) => navigator.clipboard.writeText(text)

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3.5 bg-white border-b border-blue-100/60">
        <div>
          <h1 className="text-sm font-semibold" style={{ color: '#0D1F17' }}>Medical Document Translation</h1>
          <p className="text-[11px] text-slate-400">Upload any medical document — AI extracts, translates, and structures the data into English</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border font-medium"
                style={{ background: '#D6F5EC', color: '#007A57', borderColor: '#B3EDD8' }}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
              <path d="M3 5h12M9 3v2m4.5 12l-1.5-3-1.5 3m-1 0h4M5 5l6 6.5M11 5l-6 6.5"
                stroke="#00B37E" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            Powered by Claude
          </span>
          {file && status !== 'processing' && (
            <button onClick={run}
              className="text-white text-xs px-4 py-2 rounded-xl font-semibold transition-all hover:shadow-lg hover:-translate-y-px"
              style={{ background: 'linear-gradient(135deg, #00E5A0, #00B37E)' }}>
              Translate document
            </button>
          )}
          {status === 'processing' && (
            <div className="flex items-center gap-2 text-xs px-4 py-2 rounded-xl"
                 style={{ background: '#D6F5EC', color: '#007A57' }}>
              <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              Translating...
            </div>
          )}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left: upload */}
        <div className="w-72 flex-shrink-0 border-r bg-white border-blue-100/60 flex flex-col overflow-hidden">
          <div className="p-3 border-b border-blue-50">
            <div
              onDrop={onDrop}
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onClick={() => inputRef.current?.click()}
              className={clsx(
                'border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all',
                dragging ? 'border-sky-400 bg-sky-50' : 'border-blue-100 hover:border-sky-300 hover:bg-blue-50/50'
              )}>
              <div className="w-12 h-12 rounded-2xl mx-auto mb-3 flex items-center justify-center"
                   style={{ background: '#D6F5EC' }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <path d="M3 5h12M9 3v2m4.5 12l-1.5-3-1.5 3m-1 0h4M5 5l6 6.5M11 5l-6 6.5M21 12l-5 9M21 12l-5-5m5 5H10"
                    stroke="#00B37E" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <p className="text-xs font-semibold" style={{ color: '#007A57' }}>Upload document</p>
              <p className="text-[10px] text-slate-400 mt-1">JPG, PNG, PDF · max 20 MB</p>
              <p className="text-[10px] text-slate-400">Polish, German, French, Spanish, Czech…</p>
              <input ref={inputRef} type="file" accept="image/*,.pdf" className="hidden"
                onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />
            </div>
          </div>

          {file && (
            <div className="p-3">
              <div className="flex items-center gap-2.5 p-3 rounded-xl border border-blue-100 bg-blue-50/40">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold"
                     style={{ background: file.type.startsWith('image/') ? '#D1FAE5' : '#FEF3C7',
                              color: file.type.startsWith('image/') ? '#059669' : '#D97706' }}>
                  {file.type.startsWith('image/') ? 'IMG' : 'PDF'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-slate-700 truncate">{file.name}</p>
                  <p className="text-[10px] text-slate-400">{(file.size / 1024).toFixed(0)} KB</p>
                </div>
                <button onClick={() => { setFile(null); setResult(null); setStatus('idle') }}
                  className="text-slate-300 hover:text-slate-500 transition-colors text-xs px-1">✕</button>
              </div>
              {status === 'idle' && (
                <button onClick={run}
                  className="mt-3 w-full text-white text-xs py-2.5 rounded-xl font-semibold transition-all hover:shadow-md"
                  style={{ background: 'linear-gradient(135deg, #00E5A0, #00B37E)' }}>
                  Translate now
                </button>
              )}
            </div>
          )}

          {/* What this does */}
          <div className="p-4 border-t border-blue-50 mt-auto">
            <p className="text-[10px] font-semibold uppercase tracking-wider mb-3" style={{ color: '#007A57' }}>
              What AI does
            </p>
            <div className="space-y-2.5">
              {[
                ['OCR', 'Reads text from image or PDF'],
                ['Translate', 'Converts to English'],
                ['Structure', 'Extracts key medical values'],
                ['Analyze', 'Flags abnormal results'],
              ].map(([step, desc]) => (
                <div key={step} className="flex items-start gap-2.5">
                  <div className="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 text-[9px] font-bold"
                       style={{ background: '#D6F5EC', color: '#00B37E' }}>{step[0]}</div>
                  <div>
                    <p className="text-[10px] font-semibold text-slate-600">{step}</p>
                    <p className="text-[10px] text-slate-400">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: result */}
        <div className="flex-1 overflow-y-auto" style={{ background: '#F8FAFC' }}>
          {status === 'processing' && <ProcessingState />}
          {status === 'error' && <ErrorState msg={error} />}
          {status === 'done' && result && (
            <TranslateResult result={result} onCopy={copy} activeTab={activeTab} setTab={setActiveTab} />
          )}
          {status === 'idle' && <EmptyState />}
        </div>
      </div>
    </div>
  )
}

function TranslateResult({
  result, onCopy, activeTab, setTab,
}: {
  result: TranslateResult
  onCopy: (t: string) => void
  activeTab: 'side' | 'findings'
  setTab: (t: 'side' | 'findings') => void
}) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    onCopy(result.translated_text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="p-5 space-y-4 max-w-3xl mx-auto">
      {/* Meta bar */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-white"
                style={{ background: 'linear-gradient(135deg, #00E5A0, #00B37E)' }}>
            {result.document_type}
          </span>
          <span className="text-[10px] text-slate-400 px-2 py-1 bg-white rounded-lg border border-blue-50">
            {result.source_language} → English
          </span>
          <span className="text-[10px] text-slate-400">{(result.processing_time_ms / 1000).toFixed(1)}s</span>
        </div>
        <div className="flex gap-2">
          <button onClick={copy}
            className="text-xs px-3 py-1.5 rounded-lg border transition-colors font-medium"
            style={{ borderColor: '#B3EDD8', color: copied ? '#00B37E' : '#94A3B8',
                     background: copied ? '#D6F5EC' : 'white' }}>
            {copied ? '✓ Copied' : 'Copy translation'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-xl w-fit" style={{ background: '#EFF6FF' }}>
        {[['side', 'Side by side'], ['findings', 'Key findings']].map(([k, label]) => (
          <button key={k} onClick={() => setTab(k as 'side' | 'findings')}
            className={clsx('text-xs px-4 py-1.5 rounded-lg font-medium transition-all',
              activeTab === k ? 'bg-white text-blue-700 shadow-sm' : 'text-slate-400 hover:text-slate-600')}>
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'side' && (
        <div className="grid grid-cols-2 gap-4">
          {/* Original */}
          <div className="bg-white border border-blue-50 rounded-2xl overflow-hidden">
            <div className="px-4 py-2.5 border-b border-blue-50 flex items-center justify-between"
                 style={{ background: '#FFF7ED' }}>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-amber-600">
                Original · {result.source_language}
              </p>
            </div>
            <pre className="p-4 text-xs text-slate-600 whitespace-pre-wrap leading-relaxed font-sans overflow-auto max-h-96">
              {result.original_text}
            </pre>
          </div>
          {/* Translated */}
          <div className="bg-white border border-blue-50 rounded-2xl overflow-hidden">
            <div className="px-4 py-2.5 border-b border-blue-50 flex items-center justify-between"
                 style={{ background: '#F0FFF4' }}>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-emerald-600">
                English Translation
              </p>
            </div>
            <pre className="p-4 text-xs text-slate-700 whitespace-pre-wrap leading-relaxed font-sans overflow-auto max-h-96">
              {result.translated_text}
            </pre>
          </div>
        </div>
      )}

      {activeTab === 'findings' && (
        <div className="space-y-4">
          {result.key_findings.length > 0 && (
            <div className="bg-white border border-blue-50 rounded-2xl overflow-hidden">
              <div className="px-4 py-2.5 border-b border-blue-50" style={{ background: '#F5F8F6' }}>
                <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: '#007A57' }}>
                  Extracted values
                </p>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ background: '#F8FAFC' }}>
                    <th className="text-left px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">Parameter</th>
                    <th className="text-right px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">Value</th>
                    <th className="text-center px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {result.key_findings.map((f, i) => (
                    <tr key={i} className="hover:bg-blue-50/30">
                      <td className="px-4 py-2.5 text-slate-600 font-medium text-xs">{f.label}</td>
                      <td className="px-4 py-2.5 text-right font-semibold font-mono text-xs"
                          style={{ color: f.flag && f.flag !== 'normal' ? '#DC2626' : '#0D1F17' }}>
                        {f.value}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        {f.flag === 'high' && <span className="text-[10px] bg-red-50 text-red-600 px-2 py-0.5 rounded-full font-medium">Elevated ↑</span>}
                        {f.flag === 'low' && <span className="text-[10px] bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full font-medium">Low ↓</span>}
                        {(!f.flag || f.flag === 'normal') && <span className="text-[10px] bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full font-medium">Normal</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {result.clinical_notes && (
            <div className="bg-white border border-blue-50 rounded-2xl overflow-hidden">
              <div className="px-4 py-2.5 border-b border-blue-50" style={{ background: '#F5F8F6' }}>
                <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: '#007A57' }}>
                  Clinical summary
                </p>
              </div>
              <p className="p-4 text-sm text-slate-600 leading-relaxed">{result.clinical_notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ProcessingState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <div className="relative w-14 h-14">
        <div className="absolute inset-0 border-2 rounded-full animate-spin"
             style={{ borderColor: '#00B37E', borderTopColor: 'transparent' }} />
        <div className="absolute inset-2 border-2 rounded-full animate-spin"
             style={{ borderColor: '#B3EDD8', borderTopColor: 'transparent', animationDirection: 'reverse', animationDuration: '0.8s' }} />
      </div>
      <div className="text-center">
        <p className="text-sm font-semibold" style={{ color: '#007A57' }}>Translating document</p>
        <p className="text-xs text-slate-400 mt-1">OCR → AI translation → structuring</p>
        <p className="text-xs text-slate-400">May take 30–60 seconds</p>
      </div>
    </div>
  )
}

function ErrorState({ msg }: { msg: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-2">
      <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-1"
           style={{ background: '#FEF2F2' }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
            stroke="#DC2626" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <p className="text-sm font-semibold text-red-600">Translation error</p>
      <p className="text-xs text-slate-400 max-w-xs text-center">{msg}</p>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-400 p-8">
      <div className="w-20 h-20 rounded-3xl flex items-center justify-center mb-2"
           style={{ background: '#F5F8F6' }}>
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
          <path d="M3 5h12M9 3v2m4.5 12l-1.5-3-1.5 3m-1 0h4M5 5l6 6.5M11 5l-6 6.5M21 12l-5 9M21 12l-5-5m5 5H10"
            stroke="#B3EDD8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <p className="text-sm font-semibold text-slate-500 text-center">Upload a document to translate</p>
      <p className="text-xs text-slate-400 text-center max-w-xs">
        Supports medical records, lab results, discharge summaries, prescriptions — in any European language.
      </p>
      <div className="flex gap-2 flex-wrap justify-center mt-2">
        {['Polish', 'German', 'French', 'Spanish', 'Czech', 'Italian'].map(lang => (
          <span key={lang} className="text-[10px] px-2.5 py-1 rounded-full border border-blue-100 text-slate-400">{lang}</span>
        ))}
      </div>
    </div>
  )
}
