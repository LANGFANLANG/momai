export type ChapterStatus = 'planned' | 'relation_ready' | 'drafting' | 'drafted' | 'reviewed'
export type DraftMode = 'generate' | 'rewrite' | 'continue' | 'expand' | 'compress' | 'polish'
export type IssueSeverity = 'low' | 'medium' | 'high'
export type IssueStatus = 'open' | 'fixed' | 'ignored'

export interface Chapter {
  id: string
  project_id: string
  parent_id: string | null
  title: string
  level: number
  order: number
  purpose: string | null
  suggested_word_count: number | null
  status: ChapterStatus
}

export type ChapterUpdate = Partial<Omit<Chapter, 'id' | 'project_id' | 'parent_id'>>

export interface ChapterRelation {
  id: string
  chapter_id: string
  previous_bridge: string | null
  next_bridge: string | null
  required_questions: string[] | null
  depends_on_facts: string[] | null
  key_points: string[] | null
  output_conclusions: string[] | null
  avoid_repeating: string[] | null
}

export type ChapterRelationUpdate = Partial<Omit<ChapterRelation, 'id' | 'chapter_id'>>

export interface ChapterDraft {
  id: string
  chapter_id: string
  version: number
  content: string
  prompt_snapshot: Record<string, unknown> | null
  generation_mode: DraftMode
  created_at: string
}

export interface ChapterSummary {
  id: string
  chapter_id: string
  summary: string
  key_conclusions: string[] | null
  used_facts: string[] | null
  forward_implications: string[] | null
}

export interface ConsistencyIssue {
  id: string
  project_id: string
  chapter_id: string | null
  severity: IssueSeverity
  type: string
  description: string
  suggestion: string | null
  status: IssueStatus
}

export type ConsistencyIssueUpdate = Partial<Omit<ConsistencyIssue, 'id' | 'project_id' | 'chapter_id'>>

export interface ExportRecord {
  id: string
  project_id: string
  format: 'markdown' | 'docx'
  file_url: string
  created_at: string
}
