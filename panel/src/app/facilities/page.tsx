'use client'
import { useState, useEffect } from 'react'
import clsx from 'clsx'
import { fetchApiKeys } from '@/lib/api'

const PLAN_LIMITS: Record<string, number> = {
  starter: 200, pro: 1000, enterprise: 5000, demo: 9999,
}

const PLAN_LABELS: Record<string, string> = {
  starter: 'Starter', pro: 'Pro', enterprise: 'Enterprise', demo: 'Demo',
}

const WARNING_THRESHOLD = 50

type ApiKey = {
  key_id: string
  name: string
  facility_name: string
  key_prefix: string
  plan: string
  scans_limit: number
  scans_this_month: number
  is_active: boolean
  created_at: string
}

export default function FacilitiesPage() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<ApiKey | null>(null)
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    fetchApiKeys()
      .then(data => setKeys(data.keys ?? []))
      .catch(() => setKeys([]))
      .finally(() => setLoading(false))
  }, [])

  const confirmDelete = () => {
    if (!deleteTarget) return
    setKeys(prev => prev.filter(k => k.key_id !== deleteTarget.key_id))
    setDeleteTarget(null)
  }

  const totalMrr = keys.reduce((a, k) => {
    const prices: Record<string, number> = { starter: 199, pro: 499, enterprise: 1499, demo: 0 }
    return a + (prices[k.plan] ?? 0)
  }, 0)

  const lowQuotaKeys = keys.filter(k =>
    k.plan !== 'demo' && (k.scans_limit - k.scans_this_month) < WARNING_THRESHOLD
  )

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-6 py-3 bg-white border-b border-gray-100">
        <div>
          <h1 className="text-base font-semibold text-gray-900">Placówki medyczne</h1>
          <p className="text-[11px] text-slate-400">Zużycie skanów i limity subskrypcji</p>
        </div>
        <button onClick={() => setShowForm(true)}
          className="bg-brand-500 text-white text-sm px-4 py-1.5 rounded-lg font-medium hover:bg-brand-600 transition-colors">
          + Dodaj placówkę
        </button>
      </header>

      {/* Low quota warning banner */}
      {lowQuotaKeys.length > 0 && (
        <div className="mx-6 mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 flex items-start gap-3">
          <span className="text-amber-500 text-lg flex-shrink-0">⚠</span>
          <div>
            <p className="text-sm font-semibold text-amber-800">Limit skanów prawie wyczerpany</p>
            <p className="text-xs text-amber-700 mt-0.5">
              {lowQuotaKeys.map(k => k.facility_name).join(', ')} —
              {' '}pozostało mniej niż {WARNING_THRESHOLD} skanów do końca miesiąca. Rozważ upgrade planu.
            </p>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* KPIs */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: 'Aktywnych placówek', value: keys.filter(k => k.is_active).length },
            { label: 'MRR (szacunkowy)',   value: `${totalMrr.toLocaleString()} zł` },
            { label: 'Skanów w tym mies.', value: keys.reduce((a, k) => a + k.scans_this_month, 0).toLocaleString() },
            { label: 'Skany łącznie (limit)', value: keys.filter(k => k.plan !== 'demo').reduce((a, k) => a + k.scans_limit, 0).toLocaleString() },
          ].map(s => (
            <div key={s.label} className="bg-white border border-gray-100 rounded-xl p-4">
              <p className="text-xs text-gray-400">{s.label}</p>
              <p className="text-2xl font-semibold text-gray-900 mt-1">{s.value}</p>
            </div>
          ))}
        </div>

        {/* Table */}
        <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {['Placówka', 'Plan', 'Zużycie skanów', 'Pozostało', 'Klucz API', 'Status', ''].map(h => (
                  <th key={h} className="text-left text-[10px] text-gray-400 font-medium uppercase tracking-wide px-4 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center">
                    <div className="flex items-center justify-center gap-2 text-sm text-slate-400">
                      <div className="w-4 h-4 border-2 rounded-full animate-spin border-brand-500 border-t-transparent" />
                      Ładowanie...
                    </div>
                  </td>
                </tr>
              ) : keys.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-sm text-gray-400">
                    Brak placówek
                  </td>
                </tr>
              ) : keys.map(k => {
                const used = k.scans_this_month
                const limit = k.scans_limit
                const remaining = limit - used
                const pct = Math.min(100, Math.round((used / limit) * 100))
                const isDemo = k.plan === 'demo'
                const isLow = !isDemo && remaining < WARNING_THRESHOLD
                const isFull = !isDemo && remaining <= 0

                return (
                  <tr key={k.key_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-lg bg-brand-50 flex items-center justify-center text-xs">🏥</div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{k.facility_name}</p>
                          <p className="text-[10px] text-gray-400">{k.name}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={clsx(
                        'text-xs px-2 py-0.5 rounded-full font-medium',
                        k.plan === 'pro' ? 'bg-brand-50 text-brand-700' :
                        k.plan === 'enterprise' ? 'bg-purple-50 text-purple-700' :
                        k.plan === 'demo' ? 'bg-gray-100 text-gray-500' :
                        'bg-gray-100 text-gray-600'
                      )}>
                        {PLAN_LABELS[k.plan] ?? k.plan}
                      </span>
                    </td>
                    <td className="px-4 py-3 min-w-[160px]">
                      {isDemo ? (
                        <span className="text-xs text-gray-400">bez limitu</span>
                      ) : (
                        <div className="space-y-1">
                          <div className="flex items-center justify-between text-[10px]">
                            <span className={clsx('font-medium', isFull ? 'text-red-600' : isLow ? 'text-amber-600' : 'text-gray-600')}>
                              {used.toLocaleString()} / {limit.toLocaleString()}
                            </span>
                            <span className="text-gray-400">{pct}%</span>
                          </div>
                          <div className="w-full h-1.5 rounded-full overflow-hidden bg-gray-100">
                            <div className={clsx('h-full rounded-full transition-all', isFull ? 'bg-red-500' : isLow ? 'bg-amber-400' : 'bg-brand-500')}
                                 style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {isDemo ? (
                        <span className="text-xs text-gray-400">∞</span>
                      ) : (
                        <span className={clsx(
                          'text-xs font-semibold',
                          isFull ? 'text-red-600' : isLow ? 'text-amber-600' : 'text-emerald-600'
                        )}>
                          {isFull ? '0 — LIMIT' : `${remaining} skanów`}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-[10px] font-mono text-gray-400">{k.key_prefix}…</td>
                    <td className="px-4 py-3">
                      <span className={clsx(
                        'text-xs px-2 py-0.5 rounded-full font-medium',
                        k.is_active ? 'bg-brand-50 text-brand-700' : 'bg-gray-100 text-gray-400'
                      )}>
                        {k.is_active ? '✓ Aktywna' : 'Nieaktywna'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => setDeleteTarget(k)}
                        className="text-xs text-red-400 hover:text-red-600 hover:bg-red-50 px-2 py-1 rounded-lg transition-colors font-medium">
                        Usuń
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Plan pricing */}
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-4">Plany cenowe</p>
          <div className="grid grid-cols-3 gap-4">
            {[
              { name: 'Starter', price: '199 zł', scans: 'Do 200 skanów/mies.', features: ['API + panel', 'Email support', 'Klucz API'], popular: false },
              { name: 'Pro', price: '499 zł', scans: 'Do 1 000 skanów/mies.', features: ['Wszystko ze Starter', 'Webhook', 'Eksport CSV', 'Priority support'], popular: true },
              { name: 'Enterprise', price: '1499 zł', scans: 'Do 5 000 skanów/mies.', features: ['Wszystko z Pro', 'Dedykowany opiekun', 'SLA 99.9%', 'RODO compliance'], popular: false },
            ].map(plan => (
              <div key={plan.name} className={clsx(
                'bg-white rounded-xl p-5 border-2 transition-all',
                plan.popular ? 'border-brand-500' : 'border-gray-100'
              )}>
                {plan.popular && (
                  <span className="text-[10px] bg-brand-50 text-brand-700 px-2 py-0.5 rounded-full font-medium mb-3 inline-block">
                    Najpopularniejszy
                  </span>
                )}
                <p className="text-sm font-semibold text-gray-900">{plan.name}</p>
                <p className="text-2xl font-semibold text-brand-600 mt-1">
                  {plan.price}<span className="text-xs text-gray-400 font-normal">/mies.</span>
                </p>
                <p className="text-xs text-gray-500 mt-1 mb-3">{plan.scans}</p>
                <ul className="space-y-1.5">
                  {plan.features.map(f => (
                    <li key={f} className="text-xs text-gray-600 flex items-start gap-1.5">
                      <span className="text-brand-500 mt-0.5">✓</span> {f}
                    </li>
                  ))}
                </ul>
                <button className={clsx(
                  'w-full mt-4 text-xs py-2 rounded-lg font-medium transition-colors',
                  plan.popular
                    ? 'bg-brand-500 text-white hover:bg-brand-600'
                    : 'border border-gray-200 text-gray-700 hover:bg-gray-50'
                )}>
                  Wybierz plan
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Delete confirm modal */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => setDeleteTarget(null)}>
          <div className="bg-white rounded-2xl p-6 w-96 shadow-xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center flex-shrink-0">
                <span className="text-red-500 text-lg">🗑</span>
              </div>
              <div>
                <h2 className="text-sm font-semibold text-gray-900">Usuń placówkę</h2>
                <p className="text-xs text-gray-400 mt-0.5">Ta operacja jest nieodwracalna</p>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-5">
              Czy na pewno chcesz usunąć placówkę{' '}
              <span className="font-semibold text-gray-900">{deleteTarget.facility_name}</span>?
              Wszystkie powiązane dane zostaną usunięte.
            </p>
            <div className="flex gap-2">
              <button onClick={() => setDeleteTarget(null)}
                className="flex-1 text-sm border border-gray-200 rounded-lg py-2 text-gray-600 hover:bg-gray-50 transition-colors">
                Anuluj
              </button>
              <button onClick={confirmDelete}
                className="flex-1 text-sm bg-red-500 text-white rounded-lg py-2 font-medium hover:bg-red-600 transition-colors">
                Usuń placówkę
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add facility modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => setShowForm(false)}>
          <div className="bg-white rounded-2xl p-6 w-96 shadow-xl" onClick={e => e.stopPropagation()}>
            <h2 className="text-base font-semibold text-gray-900 mb-4">Dodaj placówkę</h2>
            <div className="space-y-3">
              <input className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-brand-400" placeholder="Nazwa placówki" />
              <input className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-brand-400" placeholder="E-mail kontaktowy" />
              <select className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-brand-400 text-gray-700">
                <option value="">Wybierz plan</option>
                <option>Starter — 199 zł/mies.</option>
                <option>Pro — 499 zł/mies.</option>
                <option>Enterprise — 1499 zł/mies.</option>
              </select>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setShowForm(false)} className="flex-1 text-sm border border-gray-200 rounded-lg py-2 text-gray-600 hover:bg-gray-50">Anuluj</button>
              <button className="flex-1 text-sm bg-brand-500 text-white rounded-lg py-2 font-medium hover:bg-brand-600">Utwórz</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
