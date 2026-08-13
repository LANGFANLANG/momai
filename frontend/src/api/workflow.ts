import { API_BASE_URL, request } from './http'
import type {
  Chapter,
  ChapterDraft,
  ChapterRelation,
  ChapterRelationUpdate,
  ChapterSummary,
  ChapterUpdate,
  ConsistencyFixResult,
  ConsistencyIssue,
  ConsistencyIssueUpdate,
  DraftMode,
  ExportRecord,
} from '@/types/chapter'

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
})

export const workflowApi = {
  generateOutline: (projectId: string, outlinePreference?: string, force = false) =>
    request<Chapter[]>(
      `/api/projects/${projectId}/outline/generate`,
      json('POST', { outline_preference: outlinePreference, force }),
    ),
  listChapters: (projectId: string) => request<Chapter[]>(`/api/projects/${projectId}/outline`),
  updateChapter: (projectId: string, chapterId: string, payload: ChapterUpdate) =>
    request<Chapter>(`/api/projects/${projectId}/outline/${chapterId}`, json('PATCH', payload)),
  generateRelations: (projectId: string) =>
    request<ChapterRelation[]>(`/api/projects/${projectId}/relations/generate`, { method: 'POST' }),
  listRelations: (projectId: string) => request<ChapterRelation[]>(`/api/projects/${projectId}/relations`),
  updateRelation: (projectId: string, relationId: string, payload: ChapterRelationUpdate) =>
    request<ChapterRelation>(`/api/projects/${projectId}/relations/${relationId}`, json('PATCH', payload)),
  generateDraft: (chapterId: string, mode: DraftMode = 'generate', userInstruction?: string) =>
    request<ChapterDraft>(`/api/chapters/${chapterId}/drafts/generate`, json('POST', { mode, user_instruction: userInstruction })),
  listDrafts: (chapterId: string) => request<ChapterDraft[]>(`/api/chapters/${chapterId}/drafts`),
  updateDraft: (chapterId: string, draftId: string, content: string) =>
    request<ChapterDraft>(`/api/chapters/${chapterId}/drafts/${draftId}`, json('PATCH', { content })),
  loadSummary: (chapterId: string) => request<ChapterSummary>(`/api/chapters/${chapterId}/summary`),
  generateSummary: (chapterId: string) =>
    request<ChapterSummary>(`/api/chapters/${chapterId}/summary/generate`, { method: 'POST' }),
  generateReview: (projectId: string) =>
    request<ConsistencyIssue[]>(`/api/projects/${projectId}/review/generate`, { method: 'POST' }),
  listIssues: (projectId: string) => request<ConsistencyIssue[]>(`/api/projects/${projectId}/review`),
  updateIssue: (projectId: string, issueId: string, payload: ConsistencyIssueUpdate) =>
    request<ConsistencyIssue>(`/api/projects/${projectId}/review/${issueId}`, json('PATCH', payload)),
  fixIssue: (projectId: string, issueId: string) =>
    request<ConsistencyFixResult>(`/api/projects/${projectId}/review/${issueId}/fix`, { method: 'POST' }),
  exportMarkdown: (projectId: string) => request<ExportRecord>(`/api/projects/${projectId}/export/markdown`, { method: 'POST' }),
  exportDocx: (projectId: string) => request<ExportRecord>(`/api/projects/${projectId}/export/docx`, { method: 'POST' }),
  downloadUrl: (exportId: string) => `${API_BASE_URL}/api/exports/${exportId}/download`,
}
