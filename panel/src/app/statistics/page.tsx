'use client'
import { useState, useEffect } from 'react'
import { fetchStats, Stats } from '@/lib/api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'

const TYPE_LABELS: Record<string, string> = {
  morfologia: 'Morfologia', recepta: 'Recepta', wynik_laboratoryjny: 'Wynik lab.',
  ekg: 'EKG', skierowanie: 'Skierowanie', rtg_usg: 'RTG/USG', inny: 'Inne',
}

const OCEAN_COLORS = ['#0284C7', '#38BDF8', '#0369A1', '#7DD3FC', '#075985', '#BAE6FD', '#0C4A6E']

export default function StatisticsPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStats().then(setStats).finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <div className="flex items-center gap-3 text-sm" style={{ color: '#0284C7' }}>
        <div className="w-5 h-5 border-2 rounded-full animate-spin"
             style={{ borderColor: '#0284C7', borderTopColor: 'transparent' }} />
        Ładowanie statystyk...
      </div>
    </div>
  )
  if (!stats) return null

  const barData = Object.entries(stats.by_type).map(([k, v]) => ({ name: TYPE_LABELS[k] ?? k, value: v }))
  const pieData = Object.entries(stats.by_source).map(([k, v]) => ({
    name: k === 'ikz_mobile' ? 'IKZ Mobile' : k === 'panel_www' ? 'Panel www' : 'API placówki',
    value: v,
  }))

  const kpis = [
    { label: 'Skanów łącznie', value: stats.total_scans.toLocaleString(), icon: '📋', delta: '+12%' },
    { label: 'Skanów w msc.',  value: stats.scans_this_month.toLocaleString(), icon: '🗓', delta: '+8%' },
    { label: 'Dokładność OCR', value: `${stats.accuracy}%`, icon: '🎯', delta: '+0.3%' },
    { label: 'Czas (avg)',     value: `${(stats.avg_processing_ms / 1000).toFixed(1)}s`, icon: '⚡', delta: '-2%' },
  ]

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-6 py-3.5 bg-white border-b border-blue-100/60">
        <div>
          <h1 className="text-sm font-semibold" style={{ color: '#0B1A30' }}>Statystyki</h1>
          <p className="text-[11px] text-slate-400">Analiza skanowań i skuteczność OCR</p>
        </div>
        <select className="text-xs border border-blue-100 rounded-xl px-3 py-1.5 text-slate-600 bg-white focus:outline-none focus:ring-2 focus:ring-sky-200">
          <option>Czerwiec 2026</option>
          <option>Maj 2026</option>
          <option>Kwiecień 2026</option>
        </select>
      </header>

      <div className="flex-1 overflow-y-auto p-6 space-y-5 scrollbar-thin">
        {/* KPI grid */}
        <div className="grid grid-cols-4 gap-4">
          {kpis.map(k => (
            <div key={k.label} className="bg-white border border-blue-50 rounded-2xl p-4 hover:shadow-sm transition-shadow">
              <div className="flex items-center justify-between mb-2">
                <span className="text-base">{k.icon}</span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                      style={{ background: '#E0F2FE', color: '#0284C7' }}>
                  {k.delta}
                </span>
              </div>
              <p className="text-2xl font-bold" style={{ color: '#0B1A30' }}>{k.value}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">{k.label}</p>
            </div>
          ))}
        </div>

        {/* Charts */}
        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2 bg-white border border-blue-50 rounded-2xl p-5">
            <p className="text-[10px] font-semibold uppercase tracking-widest mb-4" style={{ color: '#0369A1' }}>
              Typy dokumentów
            </p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={barData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E0F2FE" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 12, border: '1px solid #BAE6FD', background: 'white' }}
                  cursor={{ fill: '#E0F2FE' }}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {barData.map((_, i) => (
                    <Cell key={i} fill={i === 0 ? '#0284C7' : i === 1 ? '#38BDF8' : '#7DD3FC'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white border border-blue-50 rounded-2xl p-5">
            <p className="text-[10px] font-semibold uppercase tracking-widest mb-4" style={{ color: '#0369A1' }}>
              Źródła skanów
            </p>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={45} outerRadius={70}
                     dataKey="value" paddingAngle={4} startAngle={90} endAngle={-270}>
                  {pieData.map((_, i) => <Cell key={i} fill={OCEAN_COLORS[i % OCEAN_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 12, border: '1px solid #BAE6FD' }} />
                <Legend iconSize={8} iconType="circle" wrapperStyle={{ fontSize: 11, color: '#64748B' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Source breakdown */}
        <div className="bg-white border border-blue-50 rounded-2xl p-5">
          <p className="text-[10px] font-semibold uppercase tracking-widest mb-4" style={{ color: '#0369A1' }}>
            Szczegóły według źródła
          </p>
          <div className="divide-y divide-blue-50">
            {Object.entries(stats.by_source).map(([k, v]) => {
              const total = Object.values(stats.by_source).reduce((a, b) => a + b, 0)
              const pct = Math.round((v / total) * 100)
              const icons: Record<string, string> = { ikz_mobile: '📱', panel_www: '🖥', api: '🔌', api_placowki: '🔌' }
              const labels: Record<string, string> = { ikz_mobile: 'IKZ Mobile', panel_www: 'Panel www', api: 'API', api_placowki: 'API placówki' }
              return (
                <div key={k} className="flex items-center gap-4 py-3">
                  <span className="text-sm text-slate-700 w-36">{icons[k] ?? '•'} {labels[k] ?? k}</span>
                  <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: '#E0F2FE' }}>
                    <div className="h-full rounded-full transition-all"
                         style={{ width: `${pct}%`, background: 'linear-gradient(90deg, #38BDF8, #0284C7)' }} />
                  </div>
                  <span className="text-sm font-semibold w-16 text-right" style={{ color: '#0B1A30' }}>{v.toLocaleString()}</span>
                  <span className="text-xs text-slate-400 w-10 text-right">{pct}%</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
