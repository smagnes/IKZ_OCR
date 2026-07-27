'use client'
import { useState } from 'react'
import clsx from 'clsx'
import { ScanResult, sendScanEmail } from '@/lib/api'

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

const ARRAY_SECTIONS: Record<string, { label: string; icon: string }> = {
  rozpoznania: { label: 'Rozpoznania', icon: '🩺' },
  zabiegi:     { label: 'Zabiegi / Procedury', icon: '🔬' },
  leki:        { label: 'Leki przepisane', icon: '💊' },
}

const META_FIELDS = new Set(['data_przyjecia', 'data_wypisu', 'zwolnienie', 'exam_date'])
const META_LABELS: Record<string, string> = {
  data_przyjecia: 'Data przyjęcia',
  data_wypisu:    'Data wypisu',
  zwolnienie:     'Zwolnienie L4',
  exam_date:      'Data badania',
}

export default function MedicalResultView({ result }: { result: ScanResult }) {
  const [copied, setCopied] = useState(false)
  const [emailModal, setEmailModal] = useState(false)
  const [emailTo, setEmailTo] = useState('')
  const [emailSending, setEmailSending] = useState(false)
  const [emailSent, setEmailSent] = useState(false)

  const copyResult = () => {
    const lines = [
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

  return (
    <div className="p-5 space-y-4">

      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <span className="inline-flex items-center px-3 py-1.5 rounded-xl text-xs font-semibold text-white"
                style={{ background: 'linear-gradient(135deg, #38BDF8, #0284C7)' }}>
            {result.doc_type_label}
          </span>
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            {result.confidence.overall > 0 && (
              <span className="text-[10px] text-slate-400">Pewność: {Math.round(result.confidence.overall * 100)}%</span>
            )}
            {result.processing_time_ms > 0 && (
              <><span className="text-[10px] text-slate-300">·</span>
              <span className="text-[10px] text-slate-400">Czas: {(result.processing_time_ms / 1000).toFixed(1)}s</span></>
            )}
            <span className="text-[10px] text-slate-300">·</span>
            <span className="text-[10px] font-mono text-slate-400">{result.scan_id.slice(0, 8)}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={copyResult}
            className="text-xs px-3 py-1.5 rounded-lg border transition-colors font-medium"
            style={{ borderColor: '#BAE6FD', color: copied ? '#0284C7' : '#94A3B8', background: copied ? '#E0F2FE' : 'white' }}>
            {copied ? '✓ Skopiowano' : 'Kopiuj'}
          </button>
          <button onClick={() => setEmailModal(true)}
            className="text-xs px-3 py-1.5 rounded-lg border bg-white font-medium hover:bg-blue-50"
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

      {/* Basic info */}
      {(result.facility || result.patient || result.doctor || result.exam_date || Object.keys(metaFields).length > 0) && (
        <Section title="Informacje podstawowe" icon="📋">
          <div className="divide-y divide-slate-50 text-xs">
            {result.facility && <InfoRow label="Placówka" value={result.facility} />}
            {result.patient && <InfoRow label="Pacjent" value={result.patient} />}
            {result.pesel_masked && <InfoRow label="PESEL" value={result.pesel_masked} mono />}
            {result.doctor && <InfoRow label="Lekarz" value={result.doctor} />}
            {result.exam_date && <InfoRow label="Data badania" value={result.exam_date} />}
            {Object.entries(metaFields).map(([k, v]) => (
              <InfoRow key={k} label={META_LABELS[k] ?? k} value={v} />
            ))}
          </div>
        </Section>
      )}

      {/* Array sections: diagnoses, procedures, meds */}
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
                <th className="text-left px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Parametr</th>
                <th className="text-right px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Wartość</th>
                <th className="text-center px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {Object.entries(labFields).map(([k, v]) => {
                const up = v.includes('↑')
                const down = v.includes('↓')
                const abnormal = up || down
                return (
                  <tr key={k} className="hover:bg-blue-50/30 transition-colors">
                    <td className="px-4 py-2 text-slate-600 font-medium text-xs">{k.replace(/_/g, ' ')}</td>
                    <td className="px-4 py-2 text-right font-semibold font-mono text-xs"
                        style={{ color: abnormal ? '#DC2626' : '#0B1A30' }}>
                      {v}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {up   && <span className="text-[10px] bg-red-50 text-red-600 px-2 py-0.5 rounded-full font-medium">↑ Podwyższony</span>}
                      {down && <span className="text-[10px] bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full font-medium">↓ Obniżony</span>}
                      {!abnormal && <span className="text-[10px] bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full font-medium">W normie</span>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </Section>
      )}

      {/* IKZ link */}
      {result.ikz_examination_id && (
        <div className="rounded-2xl p-3.5 flex items-center gap-3 border"
             style={{ background: '#E0F2FE', borderColor: '#BAE6FD' }}>
          <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: '#0284C7' }}>
            <span className="text-white text-sm">📱</span>
          </div>
          <div>
            <p className="text-xs font-semibold" style={{ color: '#0369A1' }}>Wysłano do IKZ Mobile</p>
            <p className="text-[10px] font-mono" style={{ color: '#0284C7' }}>examination_id: {result.ikz_examination_id}</p>
          </div>
        </div>
      )}

      {/* Email modal */}
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
                    style={{ borderColor: '#BAE6FD', color: '#94A3B8' }}>Anuluj</button>
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
