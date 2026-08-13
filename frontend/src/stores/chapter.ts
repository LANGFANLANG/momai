import { defineStore } from 'pinia'
import { ref } from 'vue'
import { workflowApi } from '@/api/workflow'
import type { Chapter, ChapterDraft, ChapterRelation, ChapterSummary, ConsistencyFixResult, ConsistencyIssue } from '@/types/chapter'

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

  async function updateDraft(chapterId: string, draftId: string, content: string): Promise<ChapterDraft> {
    const draft = await workflowApi.updateDraft(chapterId, draftId, content)
    const chapterDrafts = drafts.value[chapterId] ?? []
    const index = chapterDrafts.findIndex(({ id }) => id === draftId)
    if (index >= 0) chapterDrafts[index] = draft
    return draft
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

  function applyFixedDrafts(draftsToApply: ChapterDraft[]) {
    for (const draft of draftsToApply) {
      const existing = drafts.value[draft.chapter_id] ?? []
      drafts.value[draft.chapter_id] = [draft, ...existing.filter(item => item.id !== draft.id)]
    }
  }

  async function fixIssue(projectId: string, issueId: string): Promise<ConsistencyFixResult> {
    const result = await workflowApi.fixIssue(projectId, issueId)
    const index = reviewIssues.value.findIndex(item => item.id === issueId)
    if (index >= 0) reviewIssues.value.splice(index, 1, result.issue)
    applyFixedDrafts(result.drafts)
    return result
  }

  return { chapters, relations, drafts, summaries, reviewIssues, loading, loadChapters, loadRelations, loadDrafts, updateDraft, loadSummary, generateSummary, loadReviewIssues, fixIssue }
})
