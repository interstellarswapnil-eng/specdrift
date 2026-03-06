import { Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useDriftReport } from '../hooks/useDriftReport'
import { HealthBar } from '../components/ui/HealthBar'

export function OverviewPage() {
  const state = useDriftReport()

  if (state.status === 'loading') return <Skeleton title="Overview" />
  if (state.status === 'error') return <ErrorPanel error={state.error} />

  const { report } = state
  const { drifted, at_risk, healthy, total_sections } = report.summary

  const pieData = [
    { name: 'Drifted', value: drifted, fill: '#ef4444' },
    { name: 'At risk', value: at_risk, fill: '#fbbf24' },
    { name: 'Healthy', value: healthy, fill: '#34d399' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold tracking-tight">Overview</div>
        <div className="mt-1 text-sm text-slate-400">Last sync: {new Date(report.generated_at).toLocaleString()}</div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Stat label="Total sections" value={String(total_sections)} />
        <Stat label="Drifted" value={String(drifted)} />
        <Stat label="At risk" value={String(at_risk)} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="text-sm font-semibold">Health</div>
          <div className="mt-3">
            <HealthBar drifted={drifted} atRisk={at_risk} healthy={healthy} />
          </div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="text-sm font-semibold">Breakdown</div>
          <div className="mt-2 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" outerRadius={80} />
                <Tooltip contentStyle={{ background: '#0b1220', border: '1px solid #1f2937', color: '#e5e7eb' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  )
}

function Skeleton({ title }: { title: string }) {
  return (
    <div className="space-y-4">
      <div className="text-2xl font-semibold">{title}</div>
      <div className="h-24 animate-pulse rounded bg-slate-900/50" />
      <div className="h-64 animate-pulse rounded bg-slate-900/50" />
    </div>
  )
}

function ErrorPanel({ error }: { error: string }) {
  return (
    <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4">
      <div className="text-sm font-semibold text-red-200">Failed to load report</div>
      <div className="mt-2 text-sm text-red-100">{error}</div>
    </div>
  )
}
