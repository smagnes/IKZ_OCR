'use client'
import { useState, useEffect } from 'react'
import { fetchApiKeys, createApiKey, setWebhookUrl } from '@/lib/api'

const ENDPOINT_EXAMPLES = [
  {
    method: 'POST', path: '/v1/scan',
    desc: 'Skanuj dokument medyczny',
    headers: ['Authorization: Bearer <klucz>', 'X-IKZ-Silos-Id: <silos_id>  (opcjonalnie)'],
    body: 'multipart/form-data: file=<obraz>',
  },
  {
    method: 'GET', path: '/v1/documents',
    desc: 'Lista skanów',
    headers: ['Authorization: Bearer <klucz>'],
    body: '?doc_type=morfologia&page=1',
  },
  {
    method: 'GET', path: '/v1/stats',
    desc: 'Statystyki użycia',
    headers: ['Authorization: Bearer <klucz>'],
    body: '',
  },
]

const RESPONSE_EXAMPLE = `{
  "scan_id": "f47ac10b-58cc-4372-a567",
  "status": "ok",
  "doc_type": "morfologia",
  "doc_type_label": "Morfologia krwi",
  "confidence": { "text": 0.97, "values": 0.94, "overall": 0.95 },
  "patient": "Jan Kowalski",
  "pesel_masked": "85041***678",
  "exam_date": "12.05.2026",
  "fields": { "HGB": "10.2 ↓", "WBC": "5.8", "PLT": "245" },
  "alerts": ["anemia"],
  "processing_time_ms": 4312,
  "ikz_examination_id": 48210
}`

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<unknown[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ name: '', facility_name: '' })
  const [copied, setCopied] = useState<string | null>(null)
  const [webhookEdit, setWebhookEdit] = useState<string | null>(null)
  const [webhookVal, setWebhookVal] = useState('')
  const [webhookSaving, setWebhookSaving] = useState(false)

  useEffect(() => {
    fetchApiKeys().then(d => setKeys(d.keys)).finally(() => setLoading(false))
  }, [])

  const handleCreate = async () => {
    if (!form.name || !form.facility_name) return
    setCreating(true)
    try {
      const key = await createApiKey(form.name, form.facility_name)
      setKeys(prev => [...prev, key])
      setForm({ name: '', facility_name: '' })
    } finally {
      setCreating(false)
    }
  }

  const saveWebhook = async (keyId: string) => {
    setWebhookSaving(true)
    try {
      await setWebhookUrl(keyId, webhookVal)
      setKeys(prev => (prev as Record<string,unknown>[]).map(k =>
        String(k.key_id) === keyId ? { ...k, webhook_url: webhookVal || null } : k
      ))
      setWebhookEdit(null)
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Błąd')
    } finally {
      setWebhookSaving(false)
    }
  }

  const copy = (text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopied(id)
    setTimeout(() => setCopied(null), 2000)
  }

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center px-6 py-3.5 bg-white border-b border-blue-100/60">
        <div>
          <h1 className="text-sm font-semibold" style={{ color: '#0B1A30' }}>API / Integracja z IKZ Mobile</h1>
          <p className="text-[11px] text-slate-400">Klucze dostępu i dokumentacja endpointów</p>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6 space-y-5 max-w-3xl scrollbar-thin">

        {/* IKZ Mobile banner */}
        <div className="rounded-2xl p-4 flex gap-3 border"
             style={{ background: '#E0F2FE', borderColor: '#BAE6FD' }}>
          <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
               style={{ background: '#0284C7' }}>
            <span className="text-white text-base">📱</span>
          </div>
          <div>
            <p className="text-sm font-semibold" style={{ color: '#0369A1' }}>Integracja z IKZ Mobile</p>
            <p className="text-xs mt-0.5" style={{ color: '#0284C7' }}>
              Dodaj nagłówek <code className="px-1 py-0.5 rounded font-mono" style={{ background: '#BAE6FD' }}>X-IKZ-Silos-Id</code>, aby wynik OCR automatycznie trafił jako <em>examination</em> do silosu pacjenta.
            </p>
          </div>
        </div>

        {/* Keys list */}
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest mb-3" style={{ color: '#0369A1' }}>
            Twoje klucze API
          </p>
          {loading ? (
            <div className="flex items-center gap-2 text-sm" style={{ color: '#0284C7' }}>
              <div className="w-4 h-4 border-2 rounded-full animate-spin"
                   style={{ borderColor: '#0284C7', borderTopColor: 'transparent' }} />
              Ładowanie...
            </div>
          ) : (
            <div className="space-y-2">
              {(keys as Record<string, unknown>[]).map(k => (
                <div key={String(k.key_id)}
                     className="bg-white border border-blue-50 rounded-2xl p-4 hover:shadow-sm transition-shadow">
                  <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
                       style={{ background: '#E0F2FE' }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"
                        stroke="#0284C7" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-slate-800">{String(k.name ?? '')}</p>
                    <p className="text-[11px] text-slate-400">{String(k.facility_name ?? '')} · {String(k.scans_this_month ?? 0)}/{String(k.scans_limit ?? '—')} skanów msc.</p>
                  </div>
                  <div className="flex items-center gap-4 flex-wrap">
                    <div className="flex items-center gap-2 flex-1">
                      <code className="text-xs px-2.5 py-1 rounded-lg font-mono text-slate-600"
                            style={{ background: '#F0F7FF' }}>
                        {String(k.key_prefix ?? '')}••••
                      </code>
                      <span className="text-[10px] font-semibold px-2 py-1 rounded-full capitalize"
                            style={{ background: '#E0F2FE', color: '#0284C7' }}>
                        {String(k.plan ?? '')}
                      </span>
                      {Boolean(k.webhook_url) && (
                        <span className="text-[10px] px-2 py-1 rounded-full" style={{ background: '#ECFDF5', color: '#059669' }}>
                          🔗 Webhook
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <button onClick={() => copy(String(k.key_prefix ?? ''), String(k.key_id ?? ''))}
                        className="text-xs px-2.5 py-1.5 rounded-lg border transition-colors"
                        style={{ borderColor: '#BAE6FD', color: copied === String(k.key_id) ? '#0284C7' : '#94A3B8' }}>
                        {copied === String(k.key_id) ? '✓ Skopiowano' : 'Kopiuj'}
                      </button>
                      <button onClick={() => { setWebhookEdit(String(k.key_id)); setWebhookVal(String(k.webhook_url ?? '')) }}
                        className="text-xs px-2.5 py-1.5 rounded-lg border transition-colors"
                        style={{ borderColor: '#BAE6FD', color: '#94A3B8' }}>
                        Webhook
                      </button>
                    </div>
                  </div>
                  {webhookEdit === String(k.key_id) && (
                    <div className="mt-3 pt-3 border-t flex gap-2" style={{ borderColor: '#EFF6FF' }}>
                      <input
                        value={webhookVal}
                        onChange={e => setWebhookVal(e.target.value)}
                        placeholder="https://twojsystem.pl/webhook"
                        className="flex-1 text-xs border rounded-lg px-3 py-2 focus:outline-none"
                        style={{ borderColor: '#BAE6FD' }}
                      />
                      <button onClick={() => saveWebhook(String(k.key_id))} disabled={webhookSaving}
                        className="text-xs px-3 py-2 rounded-lg text-white font-medium disabled:opacity-50"
                        style={{ background: '#0284C7' }}>
                        {webhookSaving ? '...' : 'Zapisz'}
                      </button>
                      <button onClick={() => setWebhookEdit(null)}
                        className="text-xs px-3 py-2 rounded-lg border"
                        style={{ borderColor: '#BAE6FD', color: '#94A3B8' }}>
                        Anuluj
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Create new key */}
        <div className="bg-white border border-blue-50 rounded-2xl p-5">
          <p className="text-[10px] font-semibold uppercase tracking-widest mb-4" style={{ color: '#0369A1' }}>
            Utwórz nowy klucz dla placówki
          </p>
          <div className="flex gap-3">
            <input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
              placeholder="Nazwa (np. Produkcja)"
              className="flex-1 text-sm border rounded-xl px-3 py-2.5 focus:outline-none transition-colors"
              style={{ borderColor: '#BAE6FD' }}
              onFocus={e => e.target.style.borderColor = '#0284C7'}
              onBlur={e => e.target.style.borderColor = '#BAE6FD'} />
            <input value={form.facility_name} onChange={e => setForm(p => ({ ...p, facility_name: e.target.value }))}
              placeholder="Nazwa placówki"
              className="flex-1 text-sm border rounded-xl px-3 py-2.5 focus:outline-none transition-colors"
              style={{ borderColor: '#BAE6FD' }}
              onFocus={e => e.target.style.borderColor = '#0284C7'}
              onBlur={e => e.target.style.borderColor = '#BAE6FD'} />
            <button onClick={handleCreate} disabled={creating || !form.name || !form.facility_name}
              className="text-white text-sm px-5 py-2 rounded-xl font-semibold disabled:opacity-40 transition-all hover:shadow-md"
              style={{ background: 'linear-gradient(135deg, #38BDF8, #0284C7)' }}>
              {creating ? '...' : '+ Utwórz'}
            </button>
          </div>
        </div>

        {/* Endpoints */}
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest mb-3" style={{ color: '#0369A1' }}>
            Endpointy API
          </p>
          <div className="space-y-2">
            {ENDPOINT_EXAMPLES.map(ep => (
              <div key={ep.path} className="bg-white border border-blue-50 rounded-2xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-lg"
                        style={ep.method === 'POST'
                          ? { background: '#FFF7ED', color: '#C2410C' }
                          : { background: '#E0F2FE', color: '#0369A1' }}>
                    {ep.method}
                  </span>
                  <code className="text-xs font-mono text-slate-700">{ep.path}</code>
                  <span className="text-[11px] text-slate-400 ml-auto">{ep.desc}</span>
                </div>
                <div className="text-[10px] text-slate-400 space-y-0.5 ml-1">
                  {ep.headers.map(h => (
                    <div key={h}>
                      <span className="text-slate-300">Header: </span>
                      <code className="text-slate-500 font-mono">{h}</code>
                    </div>
                  ))}
                  {ep.body && (
                    <div>
                      <span className="text-slate-300">Body: </span>
                      <code className="text-slate-500 font-mono">{ep.body}</code>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* JSON example */}
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest mb-3" style={{ color: '#0369A1' }}>
            Przykładowa odpowiedź JSON
          </p>
          <div className="rounded-2xl p-4 overflow-x-auto scrollbar-thin" style={{ background: '#0B1A30' }}>
            <pre className="text-[11px] font-mono leading-relaxed whitespace-pre" style={{ color: '#38BDF8' }}>
              {RESPONSE_EXAMPLE}
            </pre>
          </div>
        </div>
      </div>
    </div>
  )
}
