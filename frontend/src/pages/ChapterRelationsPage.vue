<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppButton from '@/components/ui/AppButton.vue'
import { projectsApi } from '@/api/projects'
import { useChapterStore } from '@/stores/chapter'
import { workflowApi } from '@/api/workflow'
import type { ProjectBrief } from '@/types/project'

const projectId = String(useRoute().params.projectId)
const store = useChapterStore()
const selectedChapterId = ref('')
const busy = ref(false)
const message = ref('')
const brief = ref<ProjectBrief | null>(null)
const selected = computed(() => store.relations.find(item => item.chapter_id === selectedChapterId.value))
const selectedChapter = computed(() => store.chapters.find(item => item.id === selectedChapterId.value))
function list(value: string[] | null) { return (value ?? []).join('\n') }
function values(value: string) { return value.split('\n').map(item => item.trim()).filter(Boolean) }

async function load() {
  const [chapters, relations, savedBrief] = await Promise.allSettled([
    store.loadChapters(projectId),
    store.loadRelations(projectId),
    projectsApi.getBrief(projectId),
  ])
  if (chapters.status === 'fulfilled' && chapters.value[0]) {
    selectedChapterId.value = chapters.value[0].id
  }
  if (relations.status === 'rejected') message.value = '先生成章节关系以开始编辑。'
  if (savedBrief.status === 'fulfilled') brief.value = savedBrief.value
}
async function generate() {
  busy.value = true
  try {
    store.relations = await workflowApi.generateRelations(projectId)
    message.value = '章节关系已生成'
  } catch (error) {
    message.value = error instanceof Error ? error.message : '生成失败'
  } finally {
    busy.value = false
  }
}

async function save() {
  if (!selected.value) return
  busy.value = true
  try {
    await workflowApi.updateRelation(projectId, selected.value.id, selected.value)
    message.value = '当前关系已保存'
  } catch (error) {
    message.value = error instanceof Error ? error.message : '保存失败'
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>
<template>
  <section>
    <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="page-kicker">03 / RELATIONS</p>
        <h2 class="page-heading">章节关系</h2>
        <p class="page-copy mt-2">为每章保留承接、结论与避免重复的写作上下文。</p>
      </div>
      <div class="flex gap-2">
        <AppButton variant="secondary" :loading="busy" :disabled="!selected" @click="save">保存当前关系</AppButton>
        <AppButton :loading="busy" @click="generate">生成关系</AppButton>
      </div>
    </div>
    <p v-if="message" class="mb-4 text-sm text-teal-800">{{ message }}</p>
    <div class="grid gap-4 xl:grid-cols-[210px_minmax(0,1fr)_260px]">
      <aside class="panel">
        <p class="panel-heading">章节</p>
        <button
          v-for="chapter in store.chapters"
          :key="chapter.id"
          class="block w-full border-b border-stone-100 px-4 py-3 text-left text-sm hover:bg-stone-50"
          :class="selectedChapterId === chapter.id ? 'bg-teal-50 text-teal-900' : 'text-stone-700'"
          :style="{ paddingLeft: `${16 + (chapter.level - 1) * 12}px` }"
          @click="selectedChapterId = chapter.id"
        >
          {{ chapter.title }}
        </button>
      </aside>
      <div v-if="selected" class="panel">
        <div class="panel-heading">
          关系编辑
          <span class="ml-2 font-normal text-stone-500">{{ selectedChapter?.title }}</span>
        </div>
        <div class="panel-body grid gap-4 md:grid-cols-2">
          <label>
            <span class="field-label">前文承接</span>
            <textarea v-model="selected.previous_bridge" class="field-control" rows="4" />
          </label>
          <label>
            <span class="field-label">后文引出</span>
            <textarea v-model="selected.next_bridge" class="field-control" rows="4" />
          </label>
          <label>
            <span class="field-label">必须回答的问题</span>
            <textarea
              :value="list(selected.required_questions)"
              class="field-control"
              rows="5"
              @input="selected.required_questions = values(($event.target as HTMLTextAreaElement).value)"
            />
          </label>
          <label>
            <span class="field-label">关键论点</span>
            <textarea
              :value="list(selected.key_points)"
              class="field-control"
              rows="5"
              @input="selected.key_points = values(($event.target as HTMLTextAreaElement).value)"
            />
          </label>
          <label>
            <span class="field-label">输出结论</span>
            <textarea
              :value="list(selected.output_conclusions)"
              class="field-control"
              rows="4"
              @input="selected.output_conclusions = values(($event.target as HTMLTextAreaElement).value)"
            />
          </label>
          <label>
            <span class="field-label">避免重复</span>
            <textarea
              :value="list(selected.avoid_repeating)"
              class="field-control"
              rows="4"
              @input="selected.avoid_repeating = values(($event.target as HTMLTextAreaElement).value)"
            />
          </label>
        </div>
      </div>
      <div v-else class="panel p-8 text-sm text-stone-500">
        {{ selectedChapterId ? '当前章节尚未生成关系。' : '选择章节查看关系上下文。' }}
      </div>
      <aside class="panel self-start">
        <div class="panel-heading">写作上下文</div>
        <div class="panel-body grid gap-4 text-sm leading-6 text-stone-700">
          <div>
            <p class="field-label">章节目的</p>
            <p class="whitespace-pre-wrap">{{ selectedChapter?.purpose || '暂无章节目的' }}</p>
          </div>
          <div v-if="selected?.key_points?.length">
            <p class="field-label">关键论点</p>
            <ul class="list-disc space-y-1 pl-4">
              <li v-for="point in selected.key_points" :key="point">{{ point }}</li>
            </ul>
          </div>
          <div v-if="selected?.previous_bridge || selected?.next_bridge">
            <p class="field-label">承接提示</p>
            <p v-if="selected.previous_bridge">{{ selected.previous_bridge }}</p>
            <p v-if="selected.next_bridge" class="mt-2">{{ selected.next_bridge }}</p>
          </div>
          <div v-if="brief?.goal">
            <p class="field-label">项目目标</p>
            <p class="whitespace-pre-wrap">{{ brief.goal }}</p>
          </div>
          <div v-if="brief?.locked_facts?.length">
            <p class="field-label">锁定事实</p>
            <ul class="list-disc space-y-1 pl-4">
              <li v-for="fact in brief.locked_facts" :key="fact">{{ fact }}</li>
            </ul>
          </div>
        </div>
      </aside>
    </div>
  </section>
</template>
