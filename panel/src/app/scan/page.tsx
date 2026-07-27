'use client'
import { useState, useRef, useCallback, useEffect } from 'react'
import { scanDocument, sendScanEmail, ScanResult } from '@/lib/api'
import clsx from 'clsx'

const ALERT_LABELS: Record<string, string> = {
  anemia: 'Anemia',
  leukocytoza: 'Leukocytoza',
  hiperglikemia: 'Hiperglikemia',
  hipoglikemia: 'Hipoglikemia',
  nadcisnienie: 'Nadciśnienie tętnicze',
  niedoczynnosc_tarczycy: 'Niedoczynność tarczycy',
  nadczynnosc_tarczycy: 'Nadczynność tarczycy',
  pilne: 'PILNE',
}

// Fields that render as bullet lists
const ARRAY_SECTIONS: Record<string, { label: string; icon: string }> = {
  rozpoznania: { label: 'Rozpoznania', icon: '🩺' },
  zabiegi:     { label: 'Zabiegi / Procedury', icon: '🔬' },
  leki:        { label: 'Leki przepisane', icon: '💊' },
}

// Fields that are date/meta (shown in header info card)
const META_FIELDS = new Set(['data_przyjecia', 'data_wypisu', 'zwolnienie', 'exam_date'])

const META_LABELS: Record<string, string> = {
  data_przyjecia: 'Data przyjęcia',
  data_wypisu:    'Data wypisu',
  zwolnienie:     'Zwolnienie L4',
  exam_date:      'Data badania',
}

interface QueueItem {
  id: string
  file: File
  status: 'waiting' | 'processing' | 'done' | 'error'
  result?: ScanResult
  error?: string
}

export default function ScanPage() {
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const addFiles = useCallback((files: FileList | File[]) => {
    const items: QueueItem[] = Array.from(files).map(f => ({
      id: Math.random().toString(36).slice(2), file: f, status: 'waiting',
    }))
    setQueue(prev => [...prev, ...items])
    if (!selected && items.length) setSelected(items[0].id)
  }, [selected])

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragging(false)
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files)
  }

  const runOCR = async (itemId: string) => {
    const item = queue.find(q => q.id === itemId)
    if (!item || item.status === 'processing') return
    setQueue(prev => prev.map(q => q.id === itemId ? { ...q, status: 'processing' } : q))
    try {
      const result = await scanDocument(item.file)
      setQueue(prev => prev.map(q => q.id === itemId ? { ...q, status: 'done', result } : q))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Błąd OCR'
      setQueue(prev => prev.map(q => q.id === itemId ? { ...q, status: 'error', error: msg } : q))
    }
  }

  const runAll = () => queue.filter(q => q.status === 'waiting').forEach(q => runOCR(q.id))
  const selectedItem = queue.find(q => q.id === selected)

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-6 py-3.5 bg-white border-b border-blue-100/60">
        <div>
          <h1 className="text-sm font-semibold" style={{ color: '#0B1A30' }}>Nowe skanowanie</h1>
          <p className="text-[11px] text-slate-400">Wgraj dokument medyczny — AI rozpozna typ i dane</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border font-medium"
               style={{ background: '#E0F2FE', color: '#0369A1', borderColor: '#BAE6FD' }}>
            <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: '#0284C7' }} />
            IKZ Mobile połączony
          </div>
          <button onClick={runAll}
            className="text-white text-xs px-4 py-2 rounded-xl font-semibold transition-all hover:shadow-lg hover:-translate-y-px"
            style={{ background: 'linear-gradient(135deg, #38BDF8, #0284C7)' }}>
            Uruchom OCR
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Queue panel */}
        <div className="w-64 flex-shrink-0 border-r bg-white border-blue-100/60 flex flex-col overflow-hidden">
          <div className="p-3 border-b border-blue-50">
            <div
              onDrop={onDrop}
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onClick={() => inputRef.current?.click()}
              className={clsx(
                'border-2 border-dashed rounded-2xl p-5 text-center cursor-pointer transition-all',
                dragging ? 'border-sky-400 bg-sky-50' : 'border-blue-100 hover:border-sky-300 hover:bg-blue-50/50'
              )}>
              <div className="w-10 h-10 rounded-xl mx-auto mb-2 flex items-center justify-center"
                   style={{ background: '#E0F2FE' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M12 15V3m0 0L8 7m4-4l4 4M2 17l.621 2.485A2 2 0 004.561 21h14.878a2 2 0 001.94-1.515L22 17"
                    stroke="#0284C7" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <p className="text-xs font-semibold" style={{ color: '#0369A1' }}>Wgraj dokumenty</p>
              <p className="text-[10px] text-slate-400 mt-0.5">JPG, PNG, PDF · maks. 20 MB</p>
              <input ref={inputRef} type="file" multiple accept="image/*,.pdf" className="hidden"
                onChange={e => e.target.files && addFiles(e.target.files)} />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1 scrollbar-thin">
            {queue.length === 0 && (
              <p className="text-xs text-slate-400 text-center mt-8">Brak dokumentów w kolejce</p>
            )}
            {queue.map(item => (
              <button key={item.id} onClick={() => { setSelected(item.id); if (item.status === 'waiting') runOCR(item.id) }}
                className={clsx(
                  'w-full text-left p-3 rounded-xl transition-all flex items-center gap-2.5',
                  selected === item.id ? 'bg-blue-50 border border-blue-100' : 'hover:bg-slate-50'
                )}>
                <FileThumb file={item.file} size={36} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-slate-700 truncate">{item.file.name}</p>
                  <p className="text-[10px] text-slate-400">
                    {(item.file.size / 1024).toFixed(0)} KB
                  </p>
                </div>
                <StatusDot status={item.status} />
              </button>
            ))}
          </div>
        </div>

        {/* Result panel */}
        <div className="flex-1 overflow-y-auto scrollbar-thin" style={{ background: '#F8FAFC' }}>
          {selectedItem?.status === 'done' && selectedItem.result ? (
            <ResultView result={selectedItem.result} file={selectedItem.file} />
          ) : selectedItem?.status === 'processing' ? (
            <ProcessingState />
          ) : selectedItem?.status === 'error' ? (
            <ErrorState msg={selectedItem.error ?? 'Nieznany błąd'} />
          ) : (
            <EmptyState />
          )}
        </div>
      </div>
    </div>
  )
}

// ── FILE THUMBNAIL ────────────────────────────────────────────────────────────

function FileThumb({ file, size = 40 }: { file: File; size?: number }) {
  const [src, setSrc] = useState<string | null>(null)
  useEffect(() => {
    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file)
      setSrc(url)
      return () => URL.revokeObjectURL(url)
    }
  }, [file])

  if (src) {
    return <img src={src} alt="" width={size} height={size}
      className="rounded-lg object-cover flex-shrink-0" style={{ width: size, height: size }} />
  }
  return (
    <div className="rounded-lg flex items-center justify-center flex-shrink-0 text-base font-bold"
         style={{ width: size, height: size, background: '#E0F2FE', color: '#0284C7', fontSize: size * 0.4 }}>
      PDF
    </div>
  )
}

// ── DOCUMENT PREVIEW ─────────────────────────────────────────────────────────

function DocPreview({ file }: { file: File }) {
  const [src, setSrc] = useState<string | null>(null)
  useEffect(() => {
    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file)
      setSrc(url)
      return () => URL.revokeObjectURL(url)
    }
  }, [file])

  if (src) {
    return (
      <div className="bg-white border border-blue-50 rounded-2xl overflow-hidden">
        <div className="px-4 py-2.5 border-b border-blue-50" style={{ background: '#F0F7FF' }}>
          <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: '#0369A1' }}>
            Podgląd dokumentu
          </p>
        </div>
        <div className="p-3">
          <img src={src} alt="Podgląd" className="w-full rounded-xl object-contain max-h-64 bg-slate-50" />
        </div>
      </div>
    )
  }
  // PDF preview
  return (
    <div className="bg-white border border-blue-50 rounded-2xl p-4 flex items-center gap-3">
      <div className="w-12 h-14 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold"
           style={{ background: '#FEF3C7', color: '#D97706' }}>
        PDF
      </div>
      <div>
        <p className="text-sm font-semibold text-slate-800">{file.name}</p>
        <p className="text-xs text-slate-400">{(file.size / 1024).toFixed(0)} KB · Dokument wielostronicowy</p>
      </div>
    </div>
  )
}

// ── RESULT VIEW ───────────────────────────────────────────────────────────────

function ResultView({ result, file }: { result: ScanResult; file: File }) {
  const [copied, setCopied] = useState(false)
  const [emailModal, setEmailModal] = useState(false)
  const [emailTo, setEmailTo] = useState('')
  const [emailSending, setEmailSending] = useState(false)
  const [emailSent, setEmailSent] = useState(false)

  const copyResult = () => {
    const lines: string[] = [
      `Typ: ${result.doc_type_label}`,
      result.patient ? `Pacjent: ${result.patient}` : '',
      result.exam_date ? `Data: ${result.exam_date}` : '',
      ...Object.entries(result.fields).map(([k, v]) =>
        Array.isArray(v) ? `${k}:\n  • ${(v as string[]).join('\n  • ')}` : `${k}: ${v}`
      ),
      result.alerts.length ? `Alerty: ${result.alerts.map(a => ALERT_LABELS[a] ?? a).join(', ')}` : '',
    ].filter(Boolean)
    navigator.clipboard.writeText(lines.join('\n'))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleEmail = async () => {
    if (!emailTo) return
    setEmailSending(true)
    try {
      await sendScanEmail(result.scan_id, emailTo)
      setEmailSent(true)
      setTimeout(() => { setEmailModal(false); setEmailSent(false) }, 2000)
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Błąd wysyłki')
    } finally {
      setEmailSending(false)
    }
  }

  // Categorize fields
  const metaFields: Record<string, string> = {}
  const arrayFields: Record<string, string[]> = {}
  const labFields: Record<string, string> = {}

  for (const [k, v] of Object.entries(result.fields)) {
    if (Array.isArray(v)) {
      arrayFields[k] = v as string[]
    } else if (META_FIELDS.has(k)) {
      metaFields[k] = String(v)
    } else {
      labFields[k] = String(v)
    }
  }

  const hasData = result.patient || result.doctor || result.facility ||
    Object.keys(metaFields).length > 0 || Object.keys(labFields).length > 0 ||
    Object.keys(arrayFields).length > 0

  return (
    <div className="p-5 space-y-4 max-w-2xl mx-auto">

      {/* Header bar */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-white"
                style={{ background: 'linear-gradient(135deg, #38BDF8, #0284C7)' }}>
            {result.doc_type_label}
          </span>
          <div className="flex items-center gap-2 mt-1.5">
            <span className="text-[10px] text-slate-400">Pewność: {Math.round(result.confidence.overall * 100)}%</span>
            <span className="text-[10px] text-slate-300">·</span>
            <span className="text-[10px] text-slate-400">Czas: {(result.processing_time_ms / 1000).toFixed(1)}s</span>
            <span className="text-[10px] text-slate-300">·</span>
            <span className="text-[10px] font-mono text-slate-400">{result.scan_id.slice(0, 8)}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={copyResult}
            className="text-xs px-3 py-1.5 rounded-lg border transition-colors font-medium"
            style={{ borderColor: '#BAE6FD', color: copied ? '#0284C7' : '#94A3B8',
                     background: copied ? '#E0F2FE' : 'white' }}>
            {copied ? '✓ Skopiowano' : 'Kopiuj'}
          </button>
          <button onClick={() => setEmailModal(true)}
            className="text-xs px-3 py-1.5 rounded-lg border bg-white transition-colors font-medium hover:bg-blue-50"
            style={{ borderColor: '#BAE6FD', color: '#94A3B8' }}>
            Wyślij email
          </button>
        </div>
      </div>

      {/* Alerts */}
      {result.alerts.length > 0 && (
        <div className="rounded-2xl p-3.5 border flex flex-wrap gap-2"
             style={{ background: '#FFF1F2', borderColor: '#FECDD3' }}>
          <span className="text-xs font-bold text-red-700">⚠ Alerty kliniczne:</span>
          {result.alerts.map(a => (
            <span key={a} className="text-xs font-semibold text-red-700 bg-red-100 px-2.5 py-0.5 rounded-full">
              {ALERT_LABELS[a] ?? a}
            </span>
          ))}
        </div>
      )}

      {/* Preview + basic info side by side */}
      <div className="grid grid-cols-2 gap-4">
        <DocPreview file={file} />

        <div className="bg-white border border-blue-50 rounded-2xl overflow-hidden">
          <div className="px-4 py-2.5 border-b border-blue-50" style={{ background: '#F0F7FF' }}>
            <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: '#0369A1' }}>
              Informacje podstawowe
            </p>
          </div>
          <div className="divide-y divide-slate-50 text-xs">
            {result.facility && <InfoRow label="Placówka" value={result.facility} />}
            {result.patient && <InfoRow label="Pacjent" value={result.patient} />}
            {result.pesel_masked && <InfoRow label="PESEL" value={result.pesel_masked} mono />}
            {result.doctor && <InfoRow label="Lekarz" value={result.doctor} />}
            {result.exam_date && <InfoRow label="Data badania" value={result.exam_date} />}
            {Object.entries(metaFields).map(([k, v]) => (
              <InfoRow key={k} label={META_LABELS[k] ?? k} value={v} />
            ))}
            {!hasData && (
              <p className="px-4 py-3 text-slate-400 text-[11px]">Brak danych osobowych w dokumencie</p>
            )}
          </div>
        </div>
      </div>

      {/* Array sections: rozpoznania, zabiegi, leki */}
      {Object.entries(ARRAY_SECTIONS).map(([key, { label, icon }]) => {
        const items = arrayFields[key]
        if (!items?.length) return null
        return (
          <Section key={key} title={label} icon={icon}>
            <ul className="space-y-1.5 px-4 py-3">
              {items.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="mt-0.5 text-blue-300 flex-shrink-0">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </Section>
        )
      })}

      {/* Lab values table */}
      {Object.keys(labFields).length > 0 && (
        <Section title="Wyniki badań" icon="🧪">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: '#F8FAFC' }}>
                <th className="text-left px-4 py-2 text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#64748B' }}>Parametr</th>
                <th className="text-right px-4 py-2 text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#64748B' }}>Wartość</th>
                <th className="text-center px-4 py-2 text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#64748B' }}>Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {Object.entries(labFields).map(([k, v]) => {
                const up = v.includes('↑')
                const down = v.includes('↓')
                const abnormal = up || down
                return (
                  <tr key={k} className="hover:bg-blue-50/30 transition-colors">
                    <td className="px-4 py-2.5 text-slate-600 font-medium">{k.replace(/_/g, ' ')}</td>
                    <td className="px-4 py-2.5 text-right font-semibold font-mono"
                        style={{ color: abnormal ? '#DC2626' : '#0B1A30' }}>
                      {v}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      {up && <span className="text-xs bg-red-50 text-red-600 px-2 py-0.5 rounded-full font-medium">Podwyższony ↑</span>}
                      {down && <span className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full font-medium">Obniżony ↓</span>}
                      {!abnormal && <span className="text-xs bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full font-medium">W normie</span>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </Section>
      )}

      {/* Confidence */}
      <Section title="Jakość odczytu OCR" icon="📊">
        <div className="px-4 py-3 space-y-2.5">
          <ConfBar label="Tekst" value={result.confidence.text} />
          <ConfBar label="Wartości" value={result.confidence.values} />
          <ConfBar label="Jednostki" value={result.confidence.units} />
        </div>
      </Section>

      {/* IKZ link */}
      {result.ikz_examination_id && (
        <div className="rounded-2xl p-3.5 flex items-center gap-3 border"
             style={{ background: '#E0F2FE', borderColor: '#BAE6FD' }}>
          <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
               style={{ background: '#0284C7' }}>
            <span className="text-white text-sm">📱</span>
          </div>
          <div>
            <p className="text-xs font-semibold" style={{ color: '#0369A1' }}>Wysłano do IKZ Mobile</p>
            <p className="text-[10px] font-mono" style={{ color: '#0284C7' }}>
              examination_id: {result.ikz_examination_id}
            </p>
          </div>
        </div>
      )}

      {emailModal && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
             onClick={() => setEmailModal(false)}>
          <div className="bg-white rounded-2xl p-6 w-80 shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-sm font-semibold mb-3" style={{ color: '#0B1A30' }}>Wyślij wynik na email</h3>
            {emailSent ? (
              <p className="text-sm text-emerald-600 text-center py-2">✓ Wysłano!</p>
            ) : (
              <>
                <input value={emailTo} onChange={e => setEmailTo(e.target.value)}
                  type="email" placeholder="adres@email.pl"
                  className="w-full text-sm border rounded-xl px-3 py-2.5 mb-3 focus:outline-none"
                  style={{ borderColor: '#BAE6FD' }} />
                <div className="flex gap-2">
                  <button onClick={() => setEmailModal(false)}
                    className="flex-1 text-sm border rounded-xl py-2"
                    style={{ borderColor: '#BAE6FD', color: '#94A3B8' }}>
                    Anuluj
                  </button>
                  <button onClick={handleEmail} disabled={emailSending || !emailTo}
                    className="flex-1 text-sm py-2 rounded-xl text-white font-medium disabled:opacity-50"
                    style={{ background: '#0284C7' }}>
                    {emailSending ? '...' : 'Wyślij'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── SMALL COMPONENTS ──────────────────────────────────────────────────────────

function Section({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-blue-50 rounded-2xl overflow-hidden">
      <div className="px-4 py-2.5 border-b border-blue-50 flex items-center gap-2" style={{ background: '#F0F7FF' }}>
        <span className="text-sm">{icon}</span>
        <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: '#0369A1' }}>{title}</p>
      </div>
      {children}
    </div>
  )
}

function InfoRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start gap-2 px-4 py-2.5">
      <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 w-24 flex-shrink-0 pt-0.5">{label}</span>
      <span className={clsx('text-xs text-slate-700 flex-1', mono && 'font-mono')}>{value}</span>
    </div>
  )
}

function ConfBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100)
  const color = pct >= 80 ? '#059669' : pct >= 60 ? '#0284C7' : '#94A3B8'
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-slate-500 w-16">{label}</span>
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: '#E0F2FE' }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-semibold w-8 text-right" style={{ color }}>{pct}%</span>
    </div>
  )
}

function StatusDot({ status }: { status: QueueItem['status'] }) {
  const map = {
    waiting: 'bg-slate-300',
    processing: 'bg-blue-400 animate-pulse',
    done: 'bg-emerald-400',
    error: 'bg-red-400',
  }
  return <div className={clsx('w-2 h-2 rounded-full flex-shrink-0', map[status])} />
}

function ProcessingState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3">
      <div className="w-10 h-10 border-2 rounded-full animate-spin"
           style={{ borderColor: '#0284C7', borderTopColor: 'transparent' }} />
      <p className="text-sm font-medium" style={{ color: '#0369A1' }}>Przetwarzanie OCR…</p>
      <p className="text-xs text-slate-400">Może potrwać 30–90 sekund</p>
    </div>
  )
}

function ErrorState({ msg }: { msg: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-2">
      <p className="text-3xl">⚠️</p>
      <p className="text-sm font-medium text-red-600">Błąd OCR</p>
      <p className="text-xs text-slate-400 max-w-xs text-center">{msg}</p>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-2 text-slate-400">
      <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-2"
           style={{ background: '#F0F7FF' }}>
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
          <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            stroke="#BAE6FD" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <p className="text-sm font-medium text-slate-500">Wgraj dokument</p>
      <p className="text-xs text-slate-400">Wybierz plik z kolejki lub przeciągnij nowy</p>
    </div>
  )
}
