import { formatDistanceToNowStrict } from 'date-fns'
import type { DriftSection } from '../../lib/types'
import { HealthPill } from '../ui/HealthPill'

function asDate(s?: string) {
  if (!s) return null
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? null : d
}

export function SectionDetailPanel({ section }: { section: DriftSection | null }) {
  if (!section) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-sm text-slate-300">
        Select a section to see details.
      </div>
    )
  }

  const health = (section.overall_health || section.drift_status) as any
  const changed = asDate(section.changed_at || section.last_changed_at)

  const linkedJira = new Set<string>()
  ;(section.linked_jira_ids || []).forEach((x) => linkedJira.add(x))
  ;(section.linked_jira || []).forEach((x) => linkedJira.add(x))
  ;(section.drift_signals || []).forEach((sig) => (sig.linked_jira || []).forEach((x) => linkedJira.add(x)))

  const linkedPrs = new Set<string>()
  ;(section.linked_prs || []).forEach((x) => linkedPrs.add(x))
  ;(section.drift_signals || []).forEach((sig) => (sig.linked_prs || []).forEach((x) => linkedPrs.add(x)))

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs text-slate-400">Section</div>
          <div className="mt-1 text-base font-semibold leading-tight">{section.id} — {section.title}</div>
        </div>
        <HealthPill health={health === 'red' || health === 'yellow' || health === 'green' ? health : 'green'} />
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
        <Info label="Last changed" value={changed ? `${formatDistanceToNowStrict(changed)} ago` : '—'} />
        <Info label="PRD status" value={section.status || '—'} />
      </div>

      <div className="mt-4">
        <div className="text-xs font-semibold text-slate-300">Linked Jira</div>
        <ul className="mt-1 flex flex-wrap gap-2">
          {linkedJira.size === 0 ? (
            <li className="text-sm text-slate-400">None</li>
          ) : (
            [...linkedJira].map((k) => (
              <li key={k} className="rounded bg-slate-900 px-2 py-1 text-xs text-slate-200 ring-1 ring-slate-800">
                {k}
              </li>
            ))
          )}
        </ul>
      </div>

      <div className="mt-4">
        <div className="text-xs font-semibold text-slate-300">Linked PRs</div>
        <ul className="mt-1 flex flex-wrap gap-2">
          {linkedPrs.size === 0 ? (
            <li className="text-sm text-slate-400">None</li>
          ) : (
            [...linkedPrs].map((k) => (
              <li key={k} className="rounded bg-slate-900 px-2 py-1 text-xs text-slate-200 ring-1 ring-slate-800">
                {k}
              </li>
            ))
          )}
        </ul>
      </div>

      <div className="mt-4">
        <div className="text-xs font-semibold text-slate-300">Drift signals</div>
        {(!section.drift_signals || section.drift_signals.length === 0) && (
          <div className="mt-1 text-sm text-slate-400">No signals detected.</div>
        )}
        <div className="mt-2 space-y-2">
          {(section.drift_signals || []).map((sig, idx) => (
            <div key={idx} className="rounded-md border border-slate-800 bg-slate-950 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-medium text-slate-100">{sig.type}</div>
                <div className="text-xs text-slate-400">{String(sig.severity || 'unknown')}</div>
              </div>
              {sig.detail && <div className="mt-1 text-sm text-slate-300">{sig.detail}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950 p-3">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="mt-1 font-medium text-slate-100">{value}</div>
    </div>
  )
}
