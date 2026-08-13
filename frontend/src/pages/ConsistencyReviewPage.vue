<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppButton from '@/components/ui/AppButton.vue'
import { useChapterStore } from '@/stores/chapter'
import { workflowApi } from '@/api/workflow'
import type { IssueSeverity } from '@/types/chapter'

const projectId = String(useRoute().params.projectId)
const store = useChapterStore()
const busy = ref(false)
const fixingId = ref('')
const message = ref('')
const colors: Record<IssueSeverity, string> = {
  high: 'border-red-200 bg-red-50 text-red-700',
  medium: 'border-amber-200 bg-amber-50 text-amber-800',
  low: 'border-stone-200 bg-stone-50 text-stone-600',
}

function chapterTitle(chapterId: string | null) {
  if (!chapterId) return undefined
  return store.chapters.find(chapter => chapter.id === chapterId)?.title
}

async function load() {
  try {
    await store.loadReviewIssues(projectId)
  } catch {
    /* no issues yet */
  }
  try {
    await store.loadChapters(projectId)
  } catch {
    /* outline may be empty */
  }
}

async function run() {
  busy.value = true
  try {
    store.reviewIssues = await workflowApi.generateReview(projectId)
    message.value = '一致性检查已完成'
  } catch (e) {
    message.value = e instanceof Error ? e.message : '检查失败'
  } finally {
    busy.value = false
  }
}

async function update(id: string, status: 'fixed' | 'ignored') {
  const issue = await workflowApi.updateIssue(projectId, id, { status })
  const index = store.reviewIssues.findIndex(item => item.id === id)
  if (index >= 0) store.reviewIssues[index] = issue
}

async function fix(id: string) {
  fixingId.value = id
  message.value = ''
  try {
    const result = await store.fixIssue(projectId, id)
    const titles = result.drafts.map(draft => chapterTitle(draft.chapter_id) || '章节')
    const summary = result.fix_summary ? `：${result.fix_summary}` : ''
    message.value = `AI 已修复并写入写作草稿（${titles.join('、')}）${summary}`
  } catch (e) {
    message.value = e instanceof Error ? e.message : 'AI 修复失败'
  } finally {
    fixingId.value = ''
  }
}

onMounted(load)
</script>

<template>
  <section>
    <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="page-kicker">06 / REVIEW</p>
        <h2 class="page-heading">一致性校验</h2>
        <p class="page-copy mt-2">检查 Brief、章节结构和草稿之间的矛盾与缺口。</p>
      </div>
      <AppButton :loading="busy" @click="run">运行一致性检查</AppButton>
    </div>
    <p
      v-if="message"
      class="mb-4 text-sm"
      :class="message.includes('失败') ? 'text-red-700' : 'text-teal-800'"
    >
      {{ message }}
    </p>
    <div
      v-if="!store.reviewIssues.length"
      class="border-y border-stone-200 py-14 text-center text-sm text-stone-500"
    >
      运行检查后，问题会按严重程度列在这里。
    </div>
    <div v-else class="grid gap-3">
      <article
        v-for="issue in store.reviewIssues"
        :key="issue.id"
        class="panel border-l-4 p-5"
        :class="colors[issue.severity]"
        :aria-busy="fixingId === issue.id"
      >
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div class="mb-2 flex flex-wrap gap-2 text-xs">
              <span class="border border-current px-2 py-0.5">{{ issue.severity }}</span>
              <span>{{ issue.type }}</span>
              <span v-if="chapterTitle(issue.chapter_id)" class="text-stone-500">
                {{ chapterTitle(issue.chapter_id) }}
              </span>
            </div>
            <h3 class="font-semibold text-stone-900">{{ issue.description }}</h3>
            <p v-if="issue.suggestion" class="mt-2 text-sm leading-6 text-stone-600">
              建议：{{ issue.suggestion }}
            </p>
          </div>
          <div v-if="fixingId === issue.id" class="flex items-center gap-2 text-sm text-teal-800">
            <span class="h-4 w-4 animate-spin rounded-full border-2 border-teal-800 border-r-transparent" />
            正在修复写作内容…
          </div>
          <div v-else-if="issue.status === 'open'" class="flex flex-wrap gap-2">
            <AppButton :disabled="busy || Boolean(fixingId)" @click="fix(issue.id)">
              AI 修复
            </AppButton>
            <AppButton variant="secondary" :disabled="Boolean(fixingId)" @click="update(issue.id, 'ignored')">
              忽略
            </AppButton>
            <AppButton variant="secondary" :disabled="Boolean(fixingId)" @click="update(issue.id, 'fixed')">
              标记已修复
            </AppButton>
          </div>
          <span
            v-else
            class="inline-flex items-center border px-2.5 py-1 text-sm"
            :class="issue.status === 'fixed' ? 'border-teal-200 bg-teal-50 text-teal-800' : 'border-stone-200 bg-stone-50 text-stone-500'"
          >
            {{ issue.status === 'fixed' ? '已修复' : '已忽略' }}
          </span>
        </div>
      </article>
    </div>
  </section>
</template>
