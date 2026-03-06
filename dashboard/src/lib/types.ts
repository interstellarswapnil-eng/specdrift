export type DriftSeverity = 'high' | 'medium' | 'low'
export type DriftStatus = 'drifted' | 'at_risk' | 'healthy' | string
export type OverallHealth = 'red' | 'yellow' | 'green' | string

export type DriftSignal = {
  type: string
  severity: DriftSeverity | string
  detail?: string
  linked_jira?: string[]
  linked_prs?: string[]
  detected_at?: string
}

export type DriftSection = {
  id: string
  title: string
  level?: number
  parent_id?: string
  changed_at?: string
  last_changed_at?: string
  drift_status?: DriftStatus
  overall_health?: OverallHealth
  drift_signals?: DriftSignal[]
  linked_prs?: string[]
  linked_jira_ids?: string[]
  linked_jira?: string[]
  status?: string
}

export type DriftSummary = {
  total_sections: number
  drifted: number
  at_risk: number
  healthy: number
}

export type DriftReport = {
  generated_at: string
  prd_doc_id?: string
  sections: DriftSection[]
  summary: DriftSummary
}

export type HealthColor = 'red' | 'yellow' | 'green'

export type SectionNode = DriftSection & {
  children: SectionNode[]
  health: HealthColor
  depth: number
}

export type DriftEvent = {
  when: string
  section_id: string
  section_title: string
  severity: string
  type: string
  detail?: string
}
