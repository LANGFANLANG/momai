<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppButton from '@/components/ui/AppButton.vue'
import { HttpError } from '@/api/http'
import { useChapterStore } from '@/stores/chapter'
import { workflowApi } from '@/api/workflow'
import { projectsApi } from '@/api/projects'
import type { DocxStyle, PaperAbstract, ProjectReference } from '@/types/project'
import { applyCitationNumbers, isBibliographyChapter } from '@/utils/citations'

const projectId = String(useRoute().params.projectId)
const store = useChapterStore()
const busy = ref(false)
const message = ref('')
const ordered = computed(() => [...store.chapters].sort((a, b) => a.order - b.order))

const defaultStyle = (): DocxStyle => ({
  heading_east_asia: '黑体',
  heading_ascii: 'Times New Roman',
  body_east_asia: '宋体',
  body_ascii: 'Times New Roman',
  heading1_size_pt: 15,
  heading2_size_pt: 14,
  heading3_size_pt: 12,
  body_size_pt: 12,
  first_line_indent_chars: 2,
  space_before_pt: 0,
  space_after_pt: 0,
  line_spacing_multiple: 1.5,
})

const style = ref<DocxStyle>(defaultStyle())
const fontSizes = [
  { label: '小二（18 磅）', value: 18 },
  { label: '三号（16 磅）', value: 16 },
  { label: '小三（15 磅）', value: 15 },
  { label: '四号（14 磅）', value: 14 },
  { label: '小四（12 磅）', value: 12 },
  { label: '五号（10.5 磅）', value: 10.5 },
]

const abstractId = ref('')
const titleEn = ref('')
const abstractZh = ref('')
const abstractEn = ref('')
const keywordsZh = ref('')
const keywordsEn = ref('')
const references = ref<ProjectReference[]>([])

function parseKeywords(raw: string, chinese: boolean) {
  return raw
    .split(chinese ? /[；;，,]+/ : /[;,]+/)
    .map(item => item.trim())
    .filter(Boolean)
}

function formatKeywords(items: string[] | null | undefined, chinese: boolean) {
  return (items || []).filter(Boolean).join(chinese ? '；' : '; ')
}

function applyAbstract(data: PaperAbstract) {
  abstractId.value = data.id
  titleEn.value = data.title_en || ''
  abstractZh.value = data.abstract_zh || ''
  abstractEn.value = data.abstract_en || ''
  keywordsZh.value = formatKeywords(data.keywords_zh, true)
  keywordsEn.value = formatKeywords(data.keywords_en, false)
}

function hasAbstractContent() {
  return Boolean(
    titleEn.value.trim()
    || abstractZh.value.trim()
    || abstractEn.value.trim()
    || keywordsZh.value.trim()
    || keywordsEn.value.trim(),
  )
}

const abstractPreview = computed(() => {
  const parts: string[] = []
  if (abstractZh.value.trim()) {
    parts.push(`# 摘要\n\n${abstractZh.value.trim()}`)
    if (keywordsZh.value.trim()) parts.push(`关键词：${keywordsZh.value.trim()}`)
  }
  if (abstractEn.value.trim() || titleEn.value.trim()) {
    parts.push('# Abstract')
    if (titleEn.value.trim()) parts.push(titleEn.value.trim())
    if (abstractEn.value.trim()) parts.push(abstractEn.value.trim())
    if (keywordsEn.value.trim()) parts.push(`Keywords: ${keywordsEn.value.trim()}`)
  }
  return parts.join('\n\n')
})

const chapterPreview = computed(() => {
  const chapters = ordered.value.filter(chapter => !isBibliographyChapter(chapter.title))
  const raw = chapters.map(chapter => store.drafts[chapter.id]?.[0]?.content || '')
  const { texts, bibliography } = applyCitationNumbers(raw, references.value)
  const parts = chapters
    .map((chapter, index) => (texts[index] ? `# ${chapter.title}\n\n${texts[index]}` : ''))
    .filter(Boolean)
  if (bibliography.length) {
    parts.push(`# 参考文献\n\n${bibliography.map(item => item.line).join('\n')}`)
  }
  return parts.join('\n\n---\n\n')
})

const preview = computed(() =>
  [abstractPreview.value, chapterPreview.value].filter(Boolean).join('\n\n---\n\n'),
)

async function saveStyle() {
  let writingPrefs: Record<string, unknown> = {}
  try {
    const context = await projectsApi.getContext(projectId)
    writingPrefs = (context.writing_prefs as Record<string, unknown> | null) || {}
  } catch {
    /* context may not exist yet */
  }
  await projectsApi.saveContext(projectId, {
    writing_prefs: { ...writingPrefs, export_docx: style.value },
  })
}

async function saveAbstract() {
  if (!abstractId.value && !hasAbstractContent()) return
  const saved = await workflowApi.saveAbstract(projectId, {
    title_en: titleEn.value.trim() || null,
    abstract_zh: abstractZh.value.trim() || null,
    abstract_en: abstractEn.value.trim() || null,
    keywords_zh: parseKeywords(keywordsZh.value, true),
    keywords_en: parseKeywords(keywordsEn.value, false),
  })
  applyAbstract(saved)
}

async function generateAbstract() {
  busy.value = true
  try {
    applyAbstract(await workflowApi.generateAbstract(projectId))
    message.value = '中英文摘要已生成，可在导出前继续修改'
  } catch (e) {
    message.value = e instanceof Error ? e.message : '摘要生成失败'
  } finally {
    busy.value = false
  }
}

async function load() {
  await store.loadChapters(projectId)
  await Promise.all(
    ordered.value.map(async chapter => {
      try {
        await store.loadDrafts(chapter.id)
      } catch {
        /* chapter has no draft */
      }
    }),
  )
  try {
    applyAbstract(await workflowApi.getAbstract(projectId))
  } catch (e) {
    if (!(e instanceof HttpError && e.status === 404)) throw e
  }
  try {
    references.value = await projectsApi.listReferences(projectId)
  } catch {
    references.value = []
  }
  try {
    const context = await projectsApi.getContext(projectId)
    const saved = context.writing_prefs?.export_docx as Partial<DocxStyle> | undefined
    style.value = { ...defaultStyle(), ...saved }
  } catch {
    style.value = defaultStyle()
  }
}

async function exportFile(format: 'markdown' | 'docx') {
  busy.value = true
  try {
    await saveAbstract()
    if (format === 'docx') await saveStyle()
    const result =
      format === 'markdown'
        ? await workflowApi.exportMarkdown(projectId)
        : await workflowApi.exportDocx(projectId, style.value)
    window.open(workflowApi.downloadUrl(result.id), '_blank')
    message.value = `${format === 'markdown' ? 'Markdown' : 'Word'} 文件已生成`
  } catch (e) {
    message.value = e instanceof Error ? e.message : '导出失败'
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  load().catch(e => {
    message.value = e instanceof Error ? e.message : '加载预览失败'
  })
})
</script>

<template>
  <section>
    <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="page-kicker">07 / EXPORT</p>
        <h2 class="page-heading">导出文稿</h2>
        <p class="page-copy mt-2">正文完成后可生成中英文摘要，再按论文常用标题与正文规范导出。</p>
      </div>
      <div class="flex gap-2">
        <AppButton variant="secondary" :loading="busy" @click="exportFile('markdown')">导出 Markdown</AppButton>
        <AppButton :loading="busy" @click="exportFile('docx')">导出 Word</AppButton>
      </div>
    </div>
    <p
      v-if="message"
      class="mb-4 text-sm"
      :class="message.includes('失败') ? 'text-red-700' : 'text-teal-800'"
    >
      {{ message }}
    </p>
    <div class="mb-4 panel">
      <div class="flex flex-wrap items-start justify-between gap-3 border-b border-stone-200 px-5 py-4">
        <div>
          <h3 class="text-sm font-semibold">中英文摘要</h3>
          <p class="mt-1 text-xs text-stone-500">文前独立内容，不写入大纲。根据已完成章节生成后可再编辑。</p>
        </div>
        <AppButton variant="secondary" :loading="busy" @click="generateAbstract">生成中英文摘要</AppButton>
      </div>
      <div class="grid gap-4 p-5 lg:grid-cols-2">
        <label class="lg:col-span-2">
          <span class="field-label">英文标题</span>
          <input v-model="titleEn" class="field-control h-9" placeholder="English title" />
        </label>
        <label>
          <span class="field-label">中文摘要</span>
          <textarea v-model="abstractZh" class="field-control min-h-36" rows="8" />
        </label>
        <label>
          <span class="field-label">英文摘要</span>
          <textarea v-model="abstractEn" class="field-control min-h-36" rows="8" />
        </label>
        <label>
          <span class="field-label">中文关键词</span>
          <input v-model="keywordsZh" class="field-control h-9" placeholder="用中文分号分隔，如 Hive；数据仓库" />
        </label>
        <label>
          <span class="field-label">英文关键词</span>
          <input v-model="keywordsEn" class="field-control h-9" placeholder="Separate with semicolons, e.g. Hive; data warehouse" />
        </label>
      </div>
    </div>
    <div class="mb-4 panel">
      <div class="border-b border-stone-200 px-5 py-4">
        <h3 class="text-sm font-semibold">Word 格式</h3>
        <p class="mt-1 text-xs text-stone-500">默认：一级黑体小三、二级黑体四号、三级黑体小四，正文宋体小四 / Times New Roman，首行缩进 2 字符，段前段后 0，1.5 倍行距。</p>
      </div>
      <div class="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
        <label>
          <span class="field-label">标题中文字体</span>
          <input v-model="style.heading_east_asia" class="field-control h-9" />
        </label>
        <label>
          <span class="field-label">一级标题字号</span>
          <select v-model.number="style.heading1_size_pt" class="field-control h-9">
            <option v-for="item in fontSizes" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>
        <label>
          <span class="field-label">二级标题字号</span>
          <select v-model.number="style.heading2_size_pt" class="field-control h-9">
            <option v-for="item in fontSizes" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>
        <label>
          <span class="field-label">三级标题字号</span>
          <select v-model.number="style.heading3_size_pt" class="field-control h-9">
            <option v-for="item in fontSizes" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>
        <label>
          <span class="field-label">正文中文字体</span>
          <input v-model="style.body_east_asia" class="field-control h-9" />
        </label>
        <label>
          <span class="field-label">正文英文字体</span>
          <input v-model="style.body_ascii" class="field-control h-9" />
        </label>
        <label>
          <span class="field-label">正文字号</span>
          <select v-model.number="style.body_size_pt" class="field-control h-9">
            <option v-for="item in fontSizes" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>
        <label>
          <span class="field-label">首行缩进（字符）</span>
          <input v-model.number="style.first_line_indent_chars" class="field-control h-9" type="number" min="0" max="4" step="0.5" />
        </label>
        <label>
          <span class="field-label">段前（磅）</span>
          <input v-model.number="style.space_before_pt" class="field-control h-9" type="number" min="0" max="24" />
        </label>
        <label>
          <span class="field-label">段后（磅）</span>
          <input v-model.number="style.space_after_pt" class="field-control h-9" type="number" min="0" max="24" />
        </label>
        <label>
          <span class="field-label">行距（倍）</span>
          <input v-model.number="style.line_spacing_multiple" class="field-control h-9" type="number" min="1" max="3" step="0.25" />
        </label>
      </div>
    </div>
    <div class="panel">
      <div class="flex items-center justify-between border-b border-stone-200 px-5 py-4">
        <h3 class="text-sm font-semibold">合并预览</h3>
        <span class="text-xs text-stone-500">{{ ordered.length }} 个章节</span>
      </div>
      <pre class="min-h-[540px] whitespace-pre-wrap p-5 font-mono text-sm leading-7 text-stone-700">{{
        preview || '暂无草稿内容。完成章节写作后，最新版本会出现在这里。'
      }}</pre>
    </div>
  </section>
</template>
