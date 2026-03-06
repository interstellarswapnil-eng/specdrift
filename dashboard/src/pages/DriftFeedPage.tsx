import { useMemo } from 'react'
import { useDriftReport } from '../hooks/useDriftReport'
import { buildDriftFeed } from '../lib/report'

export function DriftFeedPage() {
  const state = useDriftReport()

  const events = useMemo(() => {
    if (state.status !== 'ready') return []
    return buildDriftFeed(state.report)
  }, [state])

  if (state.status === 'loading') return <div className="text-sm text-slate-400">Loading…</div>
  if (state.status === 'error') {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-100">{state.error}</div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="text-2xl font-semibold tracking-tight">Drift Feed</div>
        <div className="mt-1 text-sm text-slate-400">Chronological list of detected drift events.</div>
      </div>

      <div className="rounded-lg border border-slate-800 bg-slate-950/40">
        <ul className="divide-y divide-slate-800">
          {events.length === 0 ? (
            <li className="p-4 text-sm text-slate-400">No drift events in this report.</li>
          ) : (
            events.map((e, idx) => (
              <li key={idx} className="p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div className="text-sm font-medium text-slate-100">
                    {e.type} <span className="text-slate-400">({e.severity})</span>
                  </div>
                  <div className="text-xs text-slate-400">{new Date(e.when).toLocaleString()}</div>
                </div>
                <div className="mt-1 text-sm text-slate-300">
                  <span className="font-mono text-xs text-slate-400">{e.section_id}</span> {e.section_title}
                </div>
                {e.detail && <div className="mt-2 text-sm text-slate-200">{e.detail}</div>}
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  )
}
