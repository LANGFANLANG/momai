<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppButton from '@/components/ui/AppButton.vue'
import { useChapterStore } from '@/stores/chapter'
import { workflowApi } from '@/api/workflow'
import type { Chapter, ChapterDraft, DraftMode } from '@/types/chapter'
import { extractMarkdownSection, replaceMarkdownSection } from '@/utils/markdownSections'

const route = useRoute()
const router = useRouter()
const projectId = String(route.params.projectId)
const store = useChapterStore()
const selectedId = ref(String(route.params.chapterId || ''))
const selectedDraftId = ref('')
const inheritedFrom = ref<{ chapterId: string; chapterTitle: string } | null>(null)
const mode = ref<DraftMode>('generate')
const instruction = ref('')
const content = ref('')
const savedContent = ref('')
const busy = ref(false)
const message = ref('')
const selected = computed(() => store.chapters.find(chapter => chapter.id === selectedId.value))
const sourceChapterId = computed(() => inheritedFrom.value?.chapterId || selectedId.value)
const drafts = computed(() => store.drafts[sourceChapterId.value] || [])
const isDirty = computed(() => content.value !== savedContent.value)

function ancestorsOf(chapterId: string): Chapter[] {
  const byId = new Map(store.chapters.map(chapter => [chapter.id, chapter]))
  const ancestors: Chapter[] = []
  let current = byId.get(chapterId)
  while (current?.parent_id) {
    const parent = byId.get(current.parent_id)
    if (!parent) break
    ancestors.push(parent)
    current = parent
  }
  return ancestors
}

function clearEditor() {
  inheritedFrom.value = null
  selectedDraftId.value = ''
  content.value = ''
  savedContent.value = ''
}

function applyOwnDraft(draft: ChapterDraft) {
  inheritedFrom.value = null
  selectedDraftId.value = draft.id
  content.value = draft.content
  savedContent.value = draft.content
}

function applyInheritedDraft(parent: Chapter, draft: ChapterDraft, chapter: Chapter) {
  const section = extractMarkdownSection(draft.content, chapter.title, chapter.level)
  if (!section) return false
  inheritedFrom.value = { chapterId: parent.id, chapterTitle: parent.title }
  selectedDraftId.value = draft.id
  content.value = section
  savedContent.value = section
  return true
}

function loadDraft(draftId: string) {
  const draft = drafts.value.find(item => item.id === draftId)
  const chapter = selected.value
  if (!draft || !chapter) return
  if (inheritedFrom.value) {
    const parent = store.chapters.find(item => item.id === inheritedFrom.value?.chapterId)
    if (parent && applyInheritedDraft(parent, draft, chapter)) return
    message.value = '该版本中未匹配到本节标题'
    return
  }
  applyOwnDraft(draft)
}

function chooseDraft(draftId: string) {
  if (
    draftId !== selectedDraftId.value
    && isDirty.value
    && !window.confirm('当前草稿尚未保存，仍要切换版本吗？')
  ) return
  loadDraft(draftId)
}

async function resolveContent(chapterId: string) {
  const chapter = store.chapters.find(item => item.id === chapterId)
  try {
    const ownDrafts = await store.loadDrafts(chapterId)
    if (ownDrafts[0]) {
      applyOwnDraft(ownDrafts[0])
      return
    }
    if (!chapter) {
      clearEditor()
      return
    }
    for (const ancestor of ancestorsOf(chapterId)) {
      const ancestorDrafts = store.drafts[ancestor.id]?.length
        ? store.drafts[ancestor.id]
        : await store.loadDrafts(ancestor.id)
      const latest = ancestorDrafts[0]
      if (latest && applyInheritedDraft(ancestor, latest, chapter)) return
    }
    clearEditor()
  } catch {
    clearEditor()
  }
}

async function choose(id: string) {
  if (isDirty.value && !window.confirm('当前草稿尚未保存，仍要切换章节吗？')) return
  selectedId.value = id
  await router.replace(`/projects/${projectId}/chapters/${id}`)
  await resolveContent(id)
}

async function saveDraft() {
  if (!selectedId.value || !selectedDraftId.value || !isDirty.value || !selected.value) return
  busy.value = true
  try {
    if (inheritedFrom.value) {
      const parentDraft = drafts.value.find(item => item.id === selectedDraftId.value)
      if (!parentDraft) return
      const updated = replaceMarkdownSection(
        parentDraft.content,
        selected.value.title,
        content.value,
        selected.value.level,
      )
      if (!updated) {
        message.value = `未能把本节写回「${inheritedFrom.value.chapterTitle}」草稿`
        return
      }
      const draft = await store.updateDraft(
        inheritedFrom.value.chapterId,
        selectedDraftId.value,
        updated,
      )
      const parent = store.chapters.find(item => item.id === inheritedFrom.value?.chapterId)
      if (parent) applyInheritedDraft(parent, draft, selected.value)
      message.value = `已写回「${inheritedFrom.value.chapterTitle}」版本 ${draft.version}`
    } else {
      const draft = await store.updateDraft(selectedId.value, selectedDraftId.value, content.value)
      savedContent.value = draft.content
      message.value = `版本 ${draft.version} 已保存`
    }
  } catch (error) {
    message.value = error instanceof Error ? error.message : '保存失败'
  } finally {
    busy.value = false
  }
}
async function generate() {
  if (!selectedId.value) return
  if (isDirty.value && !window.confirm('当前草稿尚未保存，生成新版本会放弃这些编辑。继续吗？')) return
  busy.value = true
  message.value = ''
  try {
    const draft = await workflowApi.generateDraft(selectedId.value, mode.value, instruction.value)
    store.drafts[selectedId.value] = [draft, ...(store.drafts[selectedId.value] || [])]
    applyOwnDraft(draft)
    message.value = `已生成第 ${draft.version} 版草稿`
  } catch (error) {
    message.value = error instanceof Error ? error.message : '生成失败'
  } finally {
    busy.value = false
  }
}
async function summary() {
  if (!selectedId.value || !selectedDraftId.value) return
  busy.value = true
  try {
    await store.generateSummary(inheritedFrom.value?.chapterId || selectedId.value)
    message.value = inheritedFrom.value
      ? `已根据「${inheritedFrom.value.chapterTitle}」草稿生成摘要`
      : '章节摘要已生成'
  } catch (error) {
    message.value = error instanceof Error ? error.message : '摘要生成失败'
  } finally {
    busy.value = false
  }
}
onMounted(async () => {
  await store.loadChapters(projectId)
  if (selectedId.value && store.chapters.some(chapter => chapter.id === selectedId.value)) {
    await choose(selectedId.value)
  } else if (store.chapters[0]) {
    await choose(store.chapters[0].id)
  }
})
watch(() => route.params.chapterId, id => {
  if (id && String(id) !== selectedId.value) choose(String(id))
})
</script>

<template>
  <section>
    <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="page-kicker">04 / WRITING</p>
        <h2 class="page-heading">章节写作</h2>
        <p class="page-copy mt-2">基于大纲与章节关系生成草稿，并保留版本记录。</p>
      </div>
      <AppButton
        variant="secondary"
        :loading="busy"
        :disabled="!selectedDraftId"
        title="需要先生成或选择一个草稿版本"
        @click="summary"
      >
        生成章节摘要
      </AppButton>
    </div>
    <p
      v-if="message"
      class="mb-4 text-sm"
      :class="message.includes('失败') ? 'text-red-700' : 'text-teal-800'"
    >
      {{ message }}
    </p>
    <div class="grid gap-4 xl:grid-cols-[200px_minmax(0,1fr)_220px]">
      <aside class="panel">
        <p class="panel-heading">大纲</p>
        <button
          v-for="chapter in store.chapters"
          :key="chapter.id"
          class="block w-full border-b border-stone-100 px-4 py-3 text-left text-sm hover:bg-stone-50"
          :class="selectedId === chapter.id ? 'bg-teal-50 text-teal-900' : 'text-stone-700'"
          :style="{ paddingLeft: `${16 + (chapter.level - 1) * 12}px` }"
          @click="choose(chapter.id)"
        >
          {{ chapter.title }}
        </button>
      </aside>
      <div class="min-w-0">
        <div class="panel">
          <div class="flex items-center justify-between border-b border-stone-200 px-5 py-4">
            <div>
              <h3 class="text-sm font-semibold">{{ selected?.title || '选择章节' }}</h3>
              <p class="mt-1 text-xs text-stone-500">{{ selected?.purpose || '暂无章节目的' }}</p>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-xs" :class="isDirty ? 'text-amber-700' : 'text-stone-500'">
                {{ isDirty ? '未保存' : '已保存' }}
              </span>
              <span class="text-xs text-stone-500">{{ content.length }} 字符</span>
              <AppButton
                variant="secondary"
                :loading="busy"
                :disabled="!selectedDraftId || !isDirty"
                @click="saveDraft"
              >
                保存
              </AppButton>
            </div>
          </div>
          <p
            v-if="inheritedFrom"
            class="border-b border-teal-200 bg-teal-50 px-5 py-3 text-sm text-teal-900"
          >
            本节内容从「{{ inheritedFrom.chapterTitle }}」草稿按标题匹配。保存会写回该上级草稿。
          </p>
          <p
            v-else-if="!selectedDraftId"
            class="border-b border-amber-200 bg-amber-50 px-5 py-3 text-sm text-amber-800"
          >
            请先在一级标题生成草稿。生成后，子标题会自动匹配对应段落。
          </p>
          <textarea
            v-model="content"
            :disabled="!selectedDraftId"
            class="block min-h-[580px] w-full border-0 bg-white p-5 font-mono text-sm leading-7 outline-none focus:ring-1 focus:ring-inset focus:ring-teal-700 disabled:cursor-not-allowed disabled:bg-stone-100 disabled:text-stone-400"
            placeholder="请先生成草稿。"
          />
        </div>
      </div>
      <aside class="grid content-start gap-4">
        <div class="panel">
          <div class="panel-heading">生成控制</div>
          <div class="panel-body grid gap-3">
            <label>
              <span class="field-label">模式</span>
              <select v-model="mode" class="field-control h-9">
                <option value="generate">生成</option>
                <option value="rewrite">改写</option>
                <option value="continue">续写</option>
                <option value="expand">扩写</option>
                <option value="compress">压缩</option>
                <option value="polish">润色</option>
              </select>
            </label>
            <label>
              <span class="field-label">补充指令</span>
              <textarea
                v-model="instruction"
                class="field-control"
                rows="4"
                placeholder="例如：更强调方法比较。"
              />
            </label>
            <AppButton :loading="busy" @click="generate">生成草稿</AppButton>
          </div>
        </div>
        <div class="panel">
          <div class="panel-heading">
            {{ inheritedFrom ? `「${inheritedFrom.chapterTitle}」草稿版本` : '草稿版本' }}
          </div>
          <button
            v-for="draft in drafts"
            :key="draft.id"
            class="block w-full border-b border-stone-100 px-4 py-3 text-left text-sm hover:bg-stone-50"
            :class="selectedDraftId === draft.id ? 'bg-teal-50 text-teal-900' : ''"
            @click="chooseDraft(draft.id)"
          >
            <span class="font-medium">版本 {{ draft.version }}</span>
            <span class="ml-2 text-xs text-stone-500">{{ draft.generation_mode }}</span>
          </button>
          <p v-if="!drafts.length" class="p-4 text-xs text-stone-500">尚无草稿版本。</p>
        </div>
      </aside>
    </div>
  </section>
</template>
