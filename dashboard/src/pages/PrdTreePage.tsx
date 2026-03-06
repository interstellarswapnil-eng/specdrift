import { useMemo, useState } from 'react'
import ReactFlow, { Background, Controls, type Edge, type Node } from 'reactflow'
import { Link, useNavigate, useParams } from 'react-router-dom'
import clsx from 'clsx'
import { useDriftReport } from '../hooks/useDriftReport'
import { buildSectionTree, getSectionById } from '../lib/report'
import type { HealthColor, SectionNode } from '../lib/types'
import { SectionDetailPanel } from '../components/sections/SectionDetailPanel'

export function PrdTreePage() {
  const state = useDriftReport()
  const { sectionId } = useParams()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  const { roots, selected, nodes, edges } = useMemo(() => {
    if (state.status !== 'ready') {
      return { roots: [] as SectionNode[], selected: null, nodes: [] as Node[], edges: [] as Edge[] }
    }

    const roots = buildSectionTree(state.report.sections)
    const selected = getSectionById(state.report, sectionId)
    const { nodes, edges } = buildFlow(roots)
    return { roots, selected, nodes, edges }
  }, [state, sectionId])

  if (state.status === 'loading') return <div className="text-sm text-slate-400">Loading…</div>
  if (state.status === 'error') {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-100">{state.error}</div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="text-2xl font-semibold tracking-tight">PRD Tree</div>
        <div className="mt-1 text-sm text-slate-400">Click a section to open the detail panel.</div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
            <div className="text-sm font-semibold">Sections</div>
            <div className="mt-2">
              <TreeList
                roots={roots}
                collapsed={collapsed}
                setCollapsed={setCollapsed}
                selectedId={sectionId}
              />
            </div>
          </div>
        </div>

        <div className="lg:col-span-5">
          <div className="h-[520px] overflow-hidden rounded-lg border border-slate-800 bg-slate-950/40">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              onNodeClick={(_, n) => navigate(`/tree/${encodeURIComponent(n.id)}`)}
            >
              <Background />
              <Controls />
            </ReactFlow>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Tip: This is a lightweight map view (React Flow). The authoritative list is the tree at left.
          </div>
        </div>

        <div className="lg:col-span-3">
          <SectionDetailPanel section={selected} />
        </div>
      </div>
    </div>
  )
}

function TreeList({
  roots,
  collapsed,
  setCollapsed,
  selectedId,
}: {
  roots: SectionNode[]
  collapsed: Record<string, boolean>
  setCollapsed: (v: Record<string, boolean>) => void
  selectedId?: string
}) {
  return (
    <ul className="space-y-1">
      {roots.map((n) => (
        <TreeNodeRow
          key={n.id}
          node={n}
          collapsed={collapsed}
          setCollapsed={setCollapsed}
          selectedId={selectedId}
        />
      ))}
    </ul>
  )
}

function TreeNodeRow({
  node,
  collapsed,
  setCollapsed,
  selectedId,
}: {
  node: SectionNode
  collapsed: Record<string, boolean>
  setCollapsed: (v: Record<string, boolean>) => void
  selectedId?: string
}) {
  const isCollapsed = collapsed[node.id] === true
  const hasKids = node.children.length > 0

  return (
    <li>
      <div className={clsx('flex items-center gap-2 rounded px-2 py-1', selectedId === node.id ? 'bg-slate-900' : 'hover:bg-slate-900/60')}>
        <button
          type="button"
          className={clsx(
            'h-6 w-6 rounded text-xs text-slate-300 hover:bg-slate-800',
            !hasKids && 'opacity-0 pointer-events-none',
          )}
          onClick={() => setCollapsed({ ...collapsed, [node.id]: !isCollapsed })}
          aria-label={isCollapsed ? 'Expand' : 'Collapse'}
        >
          {isCollapsed ? '▸' : '▾'}
        </button>

        <HealthDot health={node.health} />

        <Link to={`/tree/${encodeURIComponent(node.id)}`} className="min-w-0 flex-1 text-sm text-slate-200">
          <span className="font-mono text-xs text-slate-400">{node.id}</span>{' '}
          <span className="truncate">{node.title}</span>
        </Link>
      </div>

      {hasKids && !isCollapsed && (
        <div className="ml-7 mt-1">
          <ul className="space-y-1 border-l border-slate-800 pl-3">
            {node.children.map((c) => (
              <TreeNodeRow
                key={c.id}
                node={c}
                collapsed={collapsed}
                setCollapsed={setCollapsed}
                selectedId={selectedId}
              />
            ))}
          </ul>
        </div>
      )}
    </li>
  )
}

function HealthDot({ health }: { health: HealthColor }) {
  return (
    <span
      className={clsx(
        'inline-block h-2.5 w-2.5 rounded-full',
        health === 'red' && 'bg-red-500',
        health === 'yellow' && 'bg-amber-400',
        health === 'green' && 'bg-emerald-400',
      )}
      title={health}
    />
  )
}

function buildFlow(roots: SectionNode[]): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = []
  const edges: Edge[] = []

  const rowY = 120
  const colX = 260

  const walk = (n: SectionNode, depth: number, index: number, parentId?: string) => {
    const x = depth * colX
    const y = index * rowY

    nodes.push({
      id: n.id,
      position: { x, y },
      data: { label: `${n.id} ${n.title}` },
      style: {
        borderRadius: 10,
        border: '1px solid #1f2937',
        color: '#e5e7eb',
        background:
          n.health === 'red'
            ? 'rgba(239, 68, 68, 0.15)'
            : n.health === 'yellow'
              ? 'rgba(251, 191, 36, 0.15)'
              : 'rgba(52, 211, 153, 0.12)',
      },
    })

    if (parentId) {
      edges.push({ id: `${parentId}->${n.id}`, source: parentId, target: n.id, animated: false })
    }

    n.children.forEach((c, i) => walk(c, depth + 1, index + i + 1, n.id))
  }

  roots.forEach((r, i) => walk(r, 0, i))

  return { nodes, edges }
}
