import clsx from 'clsx'
import type { HealthColor } from '../../lib/types'

export function HealthPill({ health }: { health: HealthColor }) {
  const label = health === 'red' ? 'Drifted' : health === 'yellow' ? 'At risk' : 'Healthy'
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        health === 'red' && 'bg-red-500/10 text-red-200 ring-red-500/30',
        health === 'yellow' && 'bg-amber-400/10 text-amber-100 ring-amber-400/30',
        health === 'green' && 'bg-emerald-400/10 text-emerald-100 ring-emerald-400/30',
      )}
    >
      {label}
    </span>
  )
}
