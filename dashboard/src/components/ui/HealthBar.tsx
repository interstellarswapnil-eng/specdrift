import clsx from 'clsx'

export function HealthBar({ drifted, atRisk, healthy }: { drifted: number; atRisk: number; healthy: number }) {
  const total = Math.max(1, drifted + atRisk + healthy)
  const redPct = (drifted / total) * 100
  const yellowPct = (atRisk / total) * 100
  const greenPct = (healthy / total) * 100

  return (
    <div className="w-full">
      <div className="h-3 w-full overflow-hidden rounded bg-slate-900 ring-1 ring-slate-800">
        <div className="flex h-full w-full">
          <div className={clsx('h-full bg-red-500/80')} style={{ width: `${redPct}%` }} />
          <div className={clsx('h-full bg-amber-400/80')} style={{ width: `${yellowPct}%` }} />
          <div className={clsx('h-full bg-emerald-400/80')} style={{ width: `${greenPct}%` }} />
        </div>
      </div>
      <div className="mt-2 flex justify-between text-xs text-slate-400">
        <span>🔴 {drifted}</span>
        <span>🟡 {atRisk}</span>
        <span>🟢 {healthy}</span>
      </div>
    </div>
  )
}
