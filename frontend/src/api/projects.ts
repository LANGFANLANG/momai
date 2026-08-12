import { request } from './http'
import type {
  Project,
  ProjectBrief,
  ProjectBriefUpdate,
  ProjectContext,
  ProjectContextPayload,
  ProjectCreate,
  ProjectUpdate,
} from '@/types/project'

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
})

export const projectsApi = {
  create: (payload: ProjectCreate) => request<Project>('/api/projects', json('POST', payload)),
  list: () => request<Project[]>('/api/projects'),
  get: (projectId: string) => request<Project>(`/api/projects/${projectId}`),
  update: (projectId: string, payload: ProjectUpdate) => request<Project>(`/api/projects/${projectId}`, json('PATCH', payload)),
  remove: (projectId: string) => request<void>(`/api/projects/${projectId}`, { method: 'DELETE' }),
  saveContext: (projectId: string, payload: ProjectContextPayload) =>
    request<ProjectContext>(`/api/projects/${projectId}/context`, json('PUT', payload)),
  generateBrief: (projectId: string) => request<ProjectBrief>(`/api/projects/${projectId}/brief/generate`, { method: 'POST' }),
  updateBrief: (projectId: string, payload: ProjectBriefUpdate) =>
    request<ProjectBrief>(`/api/projects/${projectId}/brief`, json('PATCH', payload)),
}
