import { useEffect, useMemo, useState } from 'react'
import type { DriftReport } from '../lib/types'

type State =
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; report: DriftReport }

export function useDriftReport() {
  const [state, setState] = useState<State>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false

    async function run() {
      try {
        // Default path expected to be committed by `specdrift sync --deploy`.
        // You can also drop a file at dashboard/public/drift-report.json during dev.
        const res = await fetch(`${import.meta.env.BASE_URL}drift-report.json`, {
          cache: 'no-store',
        })
        if (!res.ok) {
          throw new Error(
            `Could not load drift-report.json (HTTP ${res.status}). Run: specdrift report --format json --output dashboard/public/drift-report.json`,
          )
        }
        const json = (await res.json()) as DriftReport
        if (cancelled) return
        setState({ status: 'ready', report: json })
      } catch (e) {
        if (cancelled) return
        const msg = e instanceof Error ? e.message : String(e)
        setState({ status: 'error', error: msg })
      }
    }

    run()
    return () => {
      cancelled = true
    }
  }, [])

  return useMemo(() => state, [state])
}
