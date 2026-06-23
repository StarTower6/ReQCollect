/* ── Session ── */
export interface Session {
  session_id: string
  workspace_id: string
  user_id: string
  project_name: string
  status: 'mining' | 'generating' | 'complete'
  sufficiency_score: number
  is_pinned: boolean
  tags: string[]
  created_at: string
  updated_at: string
}

/* ── Message ── */
export interface Message {
  _id?: string
  role: 'user' | 'assistant' | 'event'
  content: string
  created_at?: string
  event_type?: string
  meta?: Record<string, any>
  // Quick reply state (lives on original message)
  _quickReplies?: QrOption[]
  _qrMode?: 'single' | 'multi'
  _qrSelected?: Set<string>
  _qrDisabled?: boolean
  _qrProcessed?: boolean
}

export interface QrOption {
  label: string
  value: string
}

/* ── Profile ── */
export interface RequirementProfile {
  project_name: string
  business_background: string
  current_process: string
  user_roles: any[]
  business_flow: string
  functional_requirements: any[]
  existing_systems: any[]
  non_functional: Record<string, any>
  data_scale: string
  constraints: any[]
  success_criteria: any[]
  covered_topics: string[]
  pending_questions: string[]
  sufficiency_score: number
}

/* ── PRD ── */
export interface PrdRecord {
  id: string
  session_id: string
  version: number
  title: string
  mode: string
  sections: any[]
  markdown: string
  created_at: string
}

/* ── Dashboard ── */
export interface DashboardOverview {
  total_sessions: number
  by_status: Record<string, number>
  avg_sufficiency: number
  total_prds: number
  total_messages: number
}

export interface TrendPoint {
  date: string
  sessions: number
  prds: number
}

/* ── Field Config ── */
export interface FieldConfig {
  key: string
  label: string
  weight: number
}

export const FIELDS_CONFIG: FieldConfig[] = [
  { key: 'business_background', label: '业务背景', weight: 15 },
  { key: 'functional_requirements', label: '功能需求', weight: 15 },
  { key: 'business_flow', label: '业务流程', weight: 12 },
  { key: 'current_process', label: '当前流程', weight: 10 },
  { key: 'project_name', label: '项目名称', weight: 10 },
  { key: 'non_functional', label: '非功能需求', weight: 10 },
  { key: 'user_roles', label: '用户角色', weight: 8 },
  { key: 'existing_systems', label: '现有系统', weight: 5 },
  { key: 'data_scale', label: '数据规模', weight: 5 },
  { key: 'constraints', label: '约束条件', weight: 5 },
  { key: 'success_criteria', label: '成功标准', weight: 5 },
]

/* ── Proposal ── */
export interface Proposal {
  proposal_id: string
  workspace_id: string
  source_session_id: string
  submitter_id: string

  title: string
  background: string
  pain_points: string[]
  desired_outcome: string
  scope_note: string

  urgency: string  // 'high' | 'medium' | 'low'
  priority: string // 'P0' | 'P1' | 'P2' | 'P3'
  ai_assessment: string

  status: string  // 'pending_review' | 'approved' | 'in_development' | 'launched' | 'closed'
  tags: string[]

  created_at: string
  updated_at: string
}

export interface ProposalCreate {
  title?: string
  background?: string
  pain_points?: string[]
  desired_outcome?: string
  scope_note?: string
  urgency?: string
  tags?: string[]
  source_session_id?: string
  submitter_id?: string
}

export interface ProposalUpdate {
  title?: string
  background?: string
  pain_points?: string[]
  desired_outcome?: string
  scope_note?: string
  urgency?: string
  priority?: string
  status?: string
  ai_assessment?: string
  tags?: string[]
}
