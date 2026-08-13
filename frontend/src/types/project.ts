export type ProjectType = 'course_report' | 'thesis' | 'proposal'
export type ProjectStatus =
  | 'drafting_info'
  | 'brief_ready'
  | 'outline_ready'
  | 'relations_ready'
  | 'drafting_chapters'
  | 'review_ready'
  | 'export_ready'

export interface Project {
  id: string
  type: ProjectType
  title: string
  major: string | null
  school: string | null
  target_word_count: number | null
  language: string
  requirements: string | null
  status: ProjectStatus
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  type: ProjectType
  title: string
  major?: string | null
  school?: string | null
  target_word_count?: number | null
  language: string
  requirements?: string | null
}

export interface ProjectUpdate extends Partial<ProjectCreate> {
  status?: ProjectStatus
}

export interface ProjectContextPayload {
  background?: string | null
  problem?: string | null
  goal?: string | null
  scenario?: string | null
  target_users?: string | null
  methods?: string[] | null
  technologies?: string[] | null
  modules?: string[] | null
  architecture?: string | null
  environment?: string | null
  data_sources?: string[] | null
  experiments?: string | null
  innovations?: string[] | null
  constraints?: string[] | null
  writing_prefs?: Record<string, unknown> | null
}

export interface ProjectContext extends ProjectContextPayload {
  id: string
  project_id: string
}

export interface ProjectBrief {
  id: string
  project_id: string
  title_explanation: string | null
  background: string | null
  core_problem: string | null
  goal: string | null
  significance: string | null
  technical_route: string | null
  modules: string[] | null
  expected_result: string | null
  writing_boundary: string | null
  missing_info: string[] | null
  locked_facts: string[] | null
}

export type ProjectBriefUpdate = Partial<Omit<ProjectBrief, 'id' | 'project_id'>>

export interface FileTreeSummary {
  root: string
  total_files: number
  included_files: string[]
  ignored_summary: Record<string, number>
}

export interface CodebaseFact {
  category: string
  title: string
  content: string
  evidence_files: string[]
  confidence: string
  chapter_tags: string[]
}

export interface CodebaseAnalysis {
  summary: string
  tech_stack: Record<string, string[]>
  file_tree: FileTreeSummary
  facts: CodebaseFact[]
  missing_info: string[]
  warnings: string[]
}

export interface CodebaseAnalyzeRequest {
  root_path: string
  include_tests?: boolean
  include_docs?: boolean
  max_files?: number
  user_hint?: string | null
}

export interface CodebaseApplyResult {
  material_id: string | null
  brief_updated: boolean
  context_updated: boolean
  locked_facts_added: number
}

export interface DocxStyle {
  heading_east_asia: string
  heading_ascii: string
  body_east_asia: string
  body_ascii: string
  heading1_size_pt: number
  heading2_size_pt: number
  heading3_size_pt: number
  body_size_pt: number
  first_line_indent_chars: number
  space_before_pt: number
  space_after_pt: number
  line_spacing_multiple: number
}

export interface PaperAbstract {
  id: string
  project_id: string
  title_en: string | null
  abstract_zh: string | null
  abstract_en: string | null
  keywords_zh: string[] | null
  keywords_en: string[] | null
}

export type PaperAbstractUpdate = Partial<Omit<PaperAbstract, 'id' | 'project_id'>>

export interface ProjectReference {
  id: string
  project_id: string
  authors: string | null
  title: string
  source: string | null
  year: string | null
  extra: string | null
  sort_order: number
}

export type ProjectReferenceCreate = Pick<ProjectReference, 'title'> &
  Partial<Pick<ProjectReference, 'authors' | 'source' | 'year' | 'extra'>>

export type ProjectReferenceUpdate = Partial<Omit<ProjectReference, 'id' | 'project_id'>>

