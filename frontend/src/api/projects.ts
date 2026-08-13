import { request } from './http'
import type {
  Project,
  ProjectBrief,
  ProjectBriefUpdate,
  ProjectContext,
  ProjectContextPayload,
  ProjectCreate,
  ProjectReference,
  ProjectReferenceCreate,
  ProjectReferenceUpdate,
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
  getContext: (projectId: string) => request<ProjectContext>(`/api/projects/${projectId}/context`),
  generateBrief: (projectId: string) => request<ProjectBrief>(`/api/projects/${projectId}/brief/generate`, { method: 'POST' }),
  getBrief: (projectId: string) => request<ProjectBrief>(`/api/projects/${projectId}/brief`),
  updateBrief: (projectId: string, payload: ProjectBriefUpdate) =>
    request<ProjectBrief>(`/api/projects/${projectId}/brief`, json('PATCH', payload)),
  listReferences: (projectId: string) =>
    request<ProjectReference[]>(`/api/projects/${projectId}/references`),
  createReference: (projectId: string, payload: ProjectReferenceCreate) =>
    request<ProjectReference>(`/api/projects/${projectId}/references`, json('POST', payload)),
  updateReference: (projectId: string, referenceId: string, payload: ProjectReferenceUpdate) =>
    request<ProjectReference>(
      `/api/projects/${projectId}/references/${referenceId}`,
      json('PATCH', payload),
    ),
  deleteReference: (projectId: string, referenceId: string) =>
    request<void>(`/api/projects/${projectId}/references/${referenceId}`, { method: 'DELETE' }),
}
