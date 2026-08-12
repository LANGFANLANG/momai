import { defineStore } from 'pinia'
import { ref } from 'vue'
import { projectsApi } from '@/api/projects'
import type { Project, ProjectCreate, ProjectUpdate } from '@/types/project'

export const useProjectStore = defineStore('projects', () => {
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const loading = ref(false)

  async function loadProjects(): Promise<Project[]> {
    loading.value = true
    try {
      projects.value = await projectsApi.list()
      return projects.value
    } finally {
      loading.value = false
    }
  }

  async function loadProject(projectId: string): Promise<Project> {
    loading.value = true
    try {
      currentProject.value = await projectsApi.get(projectId)
      return currentProject.value
    } finally {
      loading.value = false
    }
  }

  async function createProject(payload: ProjectCreate): Promise<Project> {
    const project = await projectsApi.create(payload)
    projects.value.unshift(project)
    currentProject.value = project
    return project
  }

  async function updateProject(projectId: string, payload: ProjectUpdate): Promise<Project> {
    const project = await projectsApi.update(projectId, payload)
    const index = projects.value.findIndex(({ id }) => id === projectId)
    if (index >= 0) projects.value[index] = project
    if (currentProject.value?.id === projectId) currentProject.value = project
    return project
  }

  async function deleteProject(projectId: string): Promise<void> {
    await projectsApi.remove(projectId)
    projects.value = projects.value.filter(({ id }) => id !== projectId)
    if (currentProject.value?.id === projectId) currentProject.value = null
  }

  return { projects, currentProject, loading, loadProjects, loadProject, createProject, updateProject, deleteProject }
})
