import { defineStore } from 'pinia'
import { ref } from 'vue'
import { workflowApi } from '@/api/workflow'
import type { Chapter, ChapterDraft, ChapterRelation, ChapterSummary, ConsistencyIssue } from '@/types/chapter'

export const useChapterStore = defineStore('chapters', () => {
  const chapters = ref<Chapter[]>([])
  const relations = ref<ChapterRelation[]>([])
  const drafts = ref<Record<string, ChapterDraft[]>>({})
  const summaries = ref<Record<string, ChapterSummary>>({})
  const reviewIssues = ref<ConsistencyIssue[]>([])
  const loading = ref(false)

  async function loadChapters(projectId: string): Promise<Chapter[]> {
    loading.value = true
    try {
      chapters.value = await workflowApi.listChapters(projectId)
      return chapters.value
    } finally { loading.value = false }
  }

  async function loadRelations(projectId: string): Promise<ChapterRelation[]> {
    relations.value = await workflowApi.listRelations(projectId)
    return relations.value
  }

  async function loadDrafts(chapterId: string): Promise<ChapterDraft[]> {
    const chapterDrafts = await workflowApi.listDrafts(chapterId)
    drafts.value[chapterId] = chapterDrafts
    return chapterDrafts
  }

  async function loadSummary(chapterId: string): Promise<ChapterSummary> {
    const summary = await workflowApi.loadSummary(chapterId)
    summaries.value[chapterId] = summary
    return summary
  }

  async function generateSummary(chapterId: string): Promise<ChapterSummary> {
    const summary = await workflowApi.generateSummary(chapterId)
    summaries.value[chapterId] = summary
    return summary
  }

  async function loadReviewIssues(projectId: string): Promise<ConsistencyIssue[]> {
    reviewIssues.value = await workflowApi.listIssues(projectId)
    return reviewIssues.value
  }

  return { chapters, relations, drafts, summaries, reviewIssues, loading, loadChapters, loadRelations, loadDrafts, loadSummary, generateSummary, loadReviewIssues }
})
