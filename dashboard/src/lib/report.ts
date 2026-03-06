import type { DriftEvent, DriftReport, DriftSection, HealthColor, SectionNode } from './types'

function toHealth(section: DriftSection): HealthColor {
  const h = (section.overall_health || '').toLowerCase()
  if (h === 'red' || h === 'yellow' || h === 'green') return h

  const status = (section.drift_status || '').toLowerCase()
  if (status === 'drifted') return 'red'
  if (status === 'at_risk') return 'yellow'
  return 'green'
}

function inferDepth(section: DriftSection): number {
  if (typeof section.level === 'number') return Math.max(0, section.level - 1)

  // heuristic: ids like 3.1.2 or 3.1
  if (section.id && section.id.includes('.')) return section.id.split('.').length - 1
  return 0
}

export function buildSectionTree(sections: DriftSection[]): SectionNode[] {
  const byId = new Map<string, SectionNode>()
  for (const s of sections) {
    byId.set(s.id, {
      ...s,
      children: [],
      health: toHealth(s),
      depth: inferDepth(s),
    })
  }

  // parent inference: use explicit parent_id; else infer by truncating dotted id
  const roots: SectionNode[] = []
  for (const node of byId.values()) {
    let parentId = node.parent_id
    if (!parentId && node.id.includes('.')) {
      parentId = node.id.split('.').slice(0, -1).join('.')
    }

    if (parentId && byId.has(parentId)) {
      byId.get(parentId)!.children.push(node)
    } else {
      roots.push(node)
    }
  }

  // stable ordering
  const sortRec = (nodes: SectionNode[]) => {
    nodes.sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }))
    for (const n of nodes) sortRec(n.children)
  }
  sortRec(roots)

  return roots
}

export function getSectionById(report: DriftReport | null, sectionId: string | undefined) {
  if (!report || !sectionId) return null
  return report.sections.find((s) => s.id === sectionId) || null
}

export function buildDriftFeed(report: DriftReport): DriftEvent[] {
  const events: DriftEvent[] = []

  for (const s of report.sections) {
    const signals = s.drift_signals || []
    for (const sig of signals) {
      const when = sig.detected_at || s.changed_at || s.last_changed_at || report.generated_at
      events.push({
        when,
        section_id: s.id,
        section_title: s.title,
        severity: String(sig.severity || 'unknown'),
        type: sig.type,
        detail: sig.detail,
      })
    }
  }

  events.sort((a, b) => (a.when < b.when ? 1 : a.when > b.when ? -1 : 0))
  return events
}
