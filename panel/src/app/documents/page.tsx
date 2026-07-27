'use client'
import { useState, useEffect } from 'react'
import { fetchDocuments, fetchDocument, deleteDocument, exportDocumentsCsv, downloadScanTxt, downloadScanMd, downloadScanCsv, ScanResult } from '@/lib/api'
import MedicalResultView from '@/components/MedicalResultView'
import clsx from 'clsx'

const TYPE_LABELS: Record<string, string> = {
  morfologia: 'Morfologia', recepta: 'Recepta', wynik_laboratoryjny: 'Wynik lab.',
  ekg: 'EKG', skierowanie: 'Skierowanie', rtg_usg: 'RTG/USG',
  karta_informacyjna: 'Karta szpitalna', epikryza: 'Epikryza', inny: 'Inny',
}

function shortenFacility(name: string | null | undefined): string {
  if (!name) return '—'
  // Strip common suffixes and legal forms
  let s = name
    .replace(/\s+Sp\.\s*z\s*\.?o\.?o\.?.*$/i, '')
    .replace(/\s+S\.A\..*$/i, '')
    .replace(/\s+im\.\s+.{10,}$/i, m => m.slice(0, 12) + '…')
  // Trim to 28 chars
  if (s.length > 28) s = s.slice(0, 27) + '…'
  return s.trim()
}
const SOURCE_LABELS: Record<string, string> = {
  ikz_mobile: '📱 IKZ Mobile', panel_www: '🖥 Panel', api_placowki: '🔌 API', api: '🔌 API',
}
const FILTERS = ['wszystkie', 'morfologia', 'recepta', 'wynik_laboratoryjny', 'ekg',
                 'skierowanie', 'rtg_usg', 'karta_informacyjna', 'epikryza']

export default function DocumentsPage() {
  const [docs, setDocs] = useState<unknown[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('wszystkie')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detailResult, setDetailResult] = useState<ScanResult | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [deleteLabel, setDeleteLabel] = useState('')
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetchDocuments(filter !== 'wszystkie' ? { doc_type: filter } : {})
      .then(data => { setDocs(data.documents); setTotal(data.total) })
      .finally(() => setLoading(false))
  }, [filter])

  const openDetail = async (scanId: string) => {
    setSelectedId(scanId)
    setDetailResult(null)
    setDetailLoading(true)
    try {
      const result = await fetchDocument(scanId)
      setDetailResult(result)
    } catch (e) {
      console.error(e)
    } finally {
      setDetailLoading(false)
    }
  }

  const closeDetail = () => {
    setSelectedId(null)
    setDetailResult(null)
  }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteDocument(deleteTarget)
      setDocs(prev => (prev as Record<string, unknown>[]).filter(d => String(d.id) !== deleteTarget))
      setTotal(prev => prev - 1)
      if (selectedId === deleteTarget) closeDetail()
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Błąd usuwania')
    } finally {
      setDeleting(false)
      setDeleteTarget(null)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3.5 bg-white border-b border-blue-100/60">
        <div>
          <h1 className="text-sm font-semibold" style={{ color: '#0B1A30' }}>Archiwum dokumentów</h1>
          <p className="text-[11px] text-slate-400">Historia skanowań i wyniki OCR</p>
        </div>
        <div className="flex gap-2">
          {selectedId && (
            <button onClick={closeDetail}
              className="text-xs border border-blue-100 px-3 py-1.5 rounded-xl font-medium transition-colors hover:bg-blue-50"
              style={{ color: '#0284C7' }}>
              ← Lista dokumentów
            </button>
          )}
          <button onClick={() => exportDocumentsCsv().catch(e => alert(e.message))}
            className="text-xs border border-blue-100 px-3 py-1.5 rounded-xl text-slate-600 hover:bg-blue-50 transition-colors">
            Eksport CSV
          </button>
        </div>
      </header>

      {/* KPIs */}
      <div className="px-6 py-3 bg-white border-b border-blue-50 grid grid-cols-4 gap-3">
        {[
          { label: 'Dokumentów', value: total.toLocaleString() },
          { label: 'Skuteczność', value: '98.2%' },
          { label: 'Śr. czas', value: '4.3s' },
          { label: 'Placówki', value: '6' },
        ].map(s => (
          <div key={s.label} className="rounded-xl px-3 py-2" style={{ background: '#F0F7FF' }}>
            <p className="text-[10px] text-slate-400">{s.label}</p>
            <p className="text-lg font-bold mt-0.5" style={{ color: '#0B1A30' }}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="px-6 py-2.5 bg-white border-b border-blue-50 flex gap-1.5 overflow-x-auto">
        {FILTERS.map(f => (
          <button key={f} onClick={() => { setFilter(f); closeDetail() }}
            className="text-xs px-3 py-1.5 rounded-full whitespace-nowrap transition-all font-medium"
            style={filter === f
              ? { background: 'linear-gradient(135deg, #38BDF8, #0284C7)', color: 'white' }
              : { background: '#F0F7FF', color: '#475569' }}>
            {f === 'wszystkie' ? 'Wszystkie' : TYPE_LABELS[f] ?? f}
          </button>
        ))}
      </div>

      {/* Main content: table + detail panel */}
      <div className="flex flex-1 overflow-hidden">

        {/* Table */}
        <div className={clsx('flex flex-col overflow-hidden transition-all duration-300',
          selectedId ? 'w-[45%] border-r border-blue-50' : 'w-full')}>
          <div className="flex-1 overflow-y-auto scrollbar-thin">
            {loading ? (
              <div className="flex items-center justify-center h-32 gap-2 text-sm" style={{ color: '#0284C7' }}>
                <div className="w-4 h-4 border-2 rounded-full animate-spin"
                     style={{ borderColor: '#0284C7', borderTopColor: 'transparent' }} />
                Ładowanie...
              </div>
            ) : docs.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 gap-2 text-slate-400">
                <p className="text-3xl">📭</p>
                <p className="text-sm">Brak dokumentów — wgraj pierwszy skan</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-10">
                  <tr style={{ background: '#F0F7FF' }}>
                    {(selectedId
                      ? ['Placówka', 'Typ', 'Pacjent', 'Alert', '']
                      : ['Placówka', 'Typ', 'Pacjent', 'Data', 'Źródło', 'Alert', 'Pewność', 'Status', '']
                    ).map(h => (
                      <th key={h} className="text-left px-4 py-2.5"
                          style={{ fontSize: 10, color: '#0369A1', fontWeight: 600,
                                   letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y" style={{ borderColor: '#EFF6FF' }}>
                  {(docs as Record<string, unknown>[]).map(doc => {
                    const id = String(doc.id ?? '')
                    const isSelected = selectedId === id
                    return (
                      <tr key={id}
                          onClick={() => openDetail(id)}
                          className={clsx(
                            'cursor-pointer transition-colors',
                            isSelected ? 'bg-blue-50' : 'hover:bg-blue-50/40'
                          )}>
                        {/* Placówka */}
                        <td className="px-4 py-3 max-w-[180px]">
                          <p className="font-medium text-slate-700 text-xs truncate" title={String(doc.facility ?? '')}>
                            {shortenFacility(doc.facility as string)}
                          </p>
                          <p className="text-[10px] font-mono text-slate-300">{id.slice(0, 8)}</p>
                        </td>
                        {/* Typ dokumentu */}
                        <td className="px-4 py-3">
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                                style={{ background: '#E0F2FE', color: '#0284C7' }}>
                            {String(doc.doc_type_label ?? TYPE_LABELS[String(doc.doc_type ?? '')] ?? '—')}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-600 text-xs max-w-[120px] truncate"
                            title={String(doc.patient ?? '')}>
                          {String(doc.patient ?? '—')}
                        </td>
                        {!selectedId && <>
                          <td className="px-4 py-3 text-slate-400 text-xs">{String(doc.exam_date ?? '—')}</td>
                          <td className="px-4 py-3 text-slate-500 text-xs">
                            {SOURCE_LABELS[String(doc.source ?? '')] ?? String(doc.source ?? '—')}
                          </td>
                        </>}
                        <td className="px-4 py-3">
                          {Array.isArray(doc.alerts) && doc.alerts.length > 0 ? (
                            <span className="text-[10px] bg-red-50 text-red-600 border border-red-100 px-2 py-0.5 rounded-full font-medium">
                              ⚠ {String((doc.alerts as string[])[0])}
                            </span>
                          ) : <span className="text-slate-200 text-xs">—</span>}
                        </td>
                        {!selectedId && <>
                          <td className="px-4 py-3">
                            {doc.confidence_overall != null ? (
                              <div className="flex items-center gap-2">
                                <div className="w-12 h-1.5 rounded-full overflow-hidden" style={{ background: '#E0F2FE' }}>
                                  <div className="h-full rounded-full"
                                       style={{ width: `${Math.round(Number(doc.confidence_overall) * 100)}%`, background: '#0284C7' }} />
                                </div>
                                <span className="text-xs font-medium" style={{ color: '#0284C7' }}>
                                  {Math.round(Number(doc.confidence_overall) * 100)}%
                                </span>
                              </div>
                            ) : <span className="text-slate-200">—</span>}
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-xs px-2.5 py-1 rounded-full font-medium"
                                  style={{ background: '#E0F2FE', color: '#0284C7' }}>
                              ✓ Gotowe
                            </span>
                          </td>
                        </>}
                        <td className="px-4 py-3 text-right" onClick={e => e.stopPropagation()}>
                          <button
                            onClick={() => {
                              setDeleteTarget(id)
                              setDeleteLabel(String(doc.doc_type_label ?? TYPE_LABELS[String(doc.doc_type ?? '')] ?? id.slice(0, 8)))
                            }}
                            className="text-xs text-red-400 hover:text-red-600 hover:bg-red-50 px-2 py-1 rounded-lg transition-colors font-medium">
                            Usuń
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Detail panel */}
        {selectedId && (
          <div className="flex-1 flex flex-col overflow-hidden" style={{ background: '#F8FAFC' }}>
            {/* Download bar */}
            <div className="flex items-center gap-2 px-4 py-2 bg-white border-b border-blue-50">
              <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wide mr-1">Pobierz:</span>
              {(['txt','md','csv'] as const).map(ext => (
                <button key={ext}
                  onClick={() => {
                    const fn = ext === 'txt' ? downloadScanTxt : ext === 'md' ? downloadScanMd : downloadScanCsv
                    fn(selectedId).catch(e => alert(e.message))
                  }}
                  className="text-[11px] font-mono font-semibold px-2.5 py-1 rounded-lg border transition-colors hover:bg-blue-50"
                  style={{ borderColor: '#BAE6FD', color: '#0284C7' }}>
                  .{ext}
                </button>
              ))}
            </div>
            <div className="flex-1 overflow-y-auto scrollbar-thin">
              {detailLoading ? (
                <div className="flex flex-col items-center justify-center h-64 gap-3">
                  <div className="w-8 h-8 border-2 rounded-full animate-spin"
                       style={{ borderColor: '#0284C7', borderTopColor: 'transparent' }} />
                  <p className="text-sm text-slate-400">Ładowanie wyników…</p>
                </div>
              ) : detailResult ? (
                <MedicalResultView result={detailResult} />
              ) : (
                <div className="flex items-center justify-center h-64">
                  <p className="text-sm text-slate-400">Błąd ładowania dokumentu</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Delete confirm modal */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
             onClick={() => !deleting && setDeleteTarget(null)}>
          <div className="bg-white rounded-2xl p-6 w-96 shadow-xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center flex-shrink-0">
                <span className="text-red-500 text-lg">🗑</span>
              </div>
              <div>
                <h2 className="text-sm font-semibold text-slate-900">Usuń dokument</h2>
                <p className="text-xs text-slate-400 mt-0.5">Ta operacja jest nieodwracalna</p>
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-5">
              Czy na pewno chcesz usunąć <span className="font-semibold text-slate-900">{deleteLabel}</span>?
              Dane OCR i wyniki badań zostaną trwale usunięte.
            </p>
            <div className="flex gap-2">
              <button onClick={() => setDeleteTarget(null)} disabled={deleting}
                className="flex-1 text-sm border border-slate-200 rounded-xl py-2 text-slate-600 hover:bg-slate-50 transition-colors disabled:opacity-50">
                Anuluj
              </button>
              <button onClick={confirmDelete} disabled={deleting}
                className="flex-1 text-sm bg-red-500 text-white rounded-xl py-2 font-medium hover:bg-red-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                {deleting
                  ? <><div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />Usuwanie…</>
                  : 'Usuń dokument'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
