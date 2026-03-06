import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import clsx from 'clsx'

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="h-full">
      <div className="mx-auto flex h-full max-w-7xl">
        <aside className="hidden w-64 flex-none border-r border-slate-800 bg-slate-950/50 p-4 md:block">
          <div className="text-lg font-semibold tracking-tight">SpecDrift</div>
          <div className="mt-6 space-y-1">
            <SideLink to="/overview" label="Overview" />
            <SideLink to="/tree" label="PRD Tree" />
            <SideLink to="/feed" label="Drift Feed" />
          </div>
          <div className="mt-6 text-xs text-slate-400">
            Reads <code className="rounded bg-slate-900 px-1">drift-report.json</code>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="border-b border-slate-800 bg-slate-950/50 px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="text-sm text-slate-300">Dashboard</div>
              <div className="text-xs text-slate-400">Phase 3</div>
            </div>
          </header>

          <div className="p-4 md:p-6">{children}</div>
        </main>
      </div>
    </div>
  )
}

function SideLink({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        clsx(
          'block rounded px-3 py-2 text-sm',
          isActive
            ? 'bg-slate-900 text-slate-100'
            : 'text-slate-300 hover:bg-slate-900/60 hover:text-slate-100',
        )
      }
    >
      {label}
    </NavLink>
  )
}
