<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppButton from '@/components/ui/AppButton.vue'
import { projectsApi } from '@/api/projects'
import type { ProjectReference, ProjectReferenceCreate } from '@/types/project'

const projectId = String(useRoute().params.projectId)
const busy = ref(false)
const message = ref('')
const items = ref<ProjectReference[]>([])
const editingId = ref('')
const bulkText = ref('')
const form = reactive({
  authors: '',
  title: '',
  source: '',
  year: '',
  extra: '',
})

function cleanReferenceLine(line: string) {
  return line
    .trim()
    .replace(/^\s*(?:\[\d+\]|\d+[.)、．])\s*/, '')
    .replace(/\s+/g, ' ')
}

function splitReferenceText(text: string) {
  const normalized = text.replace(/\r\n/g, '\n').trim()
  if (!normalized) return []

  const numbered = normalized.match(/(?:^|\n)\s*(?:\[\d+\]|\d+[.)、．])\s*[\s\S]*?(?=(?:\n\s*(?:\[\d+\]|\d+[.)、．])\s*)|$)/g)
  const chunks = numbered?.length ? numbered : normalized.split(/\n{2,}|\n/)
  return chunks.map(cleanReferenceLine).filter(Boolean)
}

function parseReferenceLine(line: string): ProjectReferenceCreate {
  const year = line.match(/(?:19|20)\d{2}/)?.[0] || ''
  const withoutType = line.replace(/\[[A-Z]\]/gi, '').replace(/[［【][A-Z][］】]/gi, '')
  const parts = withoutType
    .split(/[.。]/)
    .map(part => part.trim())
    .filter(Boolean)
  const authors = parts.length >= 2 ? parts[0] : ''
  const title = parts.length >= 2 ? parts[1] : line.replace(/[,，]?\s*(?:19|20)\d{2}.*$/, '').trim()
  const sourceParts = parts.slice(2).join('. ')
  const source = sourceParts
    .replace(/[,，]?\s*(?:19|20)\d{2}.*$/, '')
    .trim()
  const extra = line === title ? '' : line

  return {
    authors: authors || null,
    title: title || line,
    source: source || null,
    year: year || null,
    extra: extra || null,
  }
}

function resetForm() {
  editingId.value = ''
  form.authors = ''
  form.title = ''
  form.source = ''
  form.year = ''
  form.extra = ''
}

function edit(item: ProjectReference) {
  editingId.value = item.id
  form.authors = item.authors || ''
  form.title = item.title
  form.source = item.source || ''
  form.year = item.year || ''
  form.extra = item.extra || ''
}

async function load() {
  busy.value = true
  try {
    items.value = await projectsApi.listReferences(projectId)
  } catch (error) {
    message.value = error instanceof Error ? error.message : '加载失败'
  } finally {
    busy.value = false
  }
}

async function save() {
  if (!form.title.trim()) {
    message.value = '请填写文献题名'
    return
  }
  busy.value = true
  try {
    const payload = {
      authors: form.authors.trim() || null,
      title: form.title.trim(),
      source: form.source.trim() || null,
      year: form.year.trim() || null,
      extra: form.extra.trim() || null,
    }
    if (editingId.value) {
      await projectsApi.updateReference(projectId, editingId.value, payload)
      message.value = '文献已更新'
    } else {
      await projectsApi.createReference(projectId, payload)
      message.value = '文献已添加'
    }
    resetForm()
    items.value = await projectsApi.listReferences(projectId)
  } catch (error) {
    message.value = error instanceof Error ? error.message : '保存失败'
  } finally {
    busy.value = false
  }
}

async function importBulk() {
  const references = splitReferenceText(bulkText.value).map(parseReferenceLine)
  if (!references.length) {
    message.value = '请先粘贴参考文献文本'
    return
  }

  busy.value = true
  try {
    for (const reference of references) {
      await projectsApi.createReference(projectId, reference)
    }
    bulkText.value = ''
    items.value = await projectsApi.listReferences(projectId)
    message.value = `已导入 ${references.length} 条文献`
  } catch (error) {
    message.value = error instanceof Error ? error.message : '导入失败'
  } finally {
    busy.value = false
  }
}

async function remove(item: ProjectReference) {
  busy.value = true
  try {
    await projectsApi.deleteReference(projectId, item.id)
    if (editingId.value === item.id) resetForm()
    items.value = await projectsApi.listReferences(projectId)
    message.value = '文献已删除'
  } catch (error) {
    message.value = error instanceof Error ? error.message : '删除失败'
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  load().catch(error => {
    message.value = error instanceof Error ? error.message : '加载失败'
  })
})
</script>

<template>
  <section>
    <div class="mb-6">
      <p class="page-kicker">04 / REFERENCES</p>
      <h2 class="page-heading">参考文献</h2>
      <p class="page-copy mt-2">
        可以逐条填写，也可以整段粘贴参考文献列表批量导入。写作时会按这些条目引用；导出时按正文中第一次出现的顺序编为 [1]、[2]、[3]。
      </p>
    </div>
    <p
      v-if="message"
      class="mb-4 text-sm"
      :class="message.includes('失败') ? 'text-red-700' : 'text-teal-800'"
    >
      {{ message }}
    </p>
    <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <div class="panel">
        <div class="border-b border-stone-200 px-5 py-4">
          <h3 class="text-sm font-semibold">批量粘贴</h3>
        </div>
        <div class="grid gap-3 border-b border-stone-200 p-5">
          <label>
            <span class="field-label">文献文本</span>
            <textarea
              v-model="bulkText"
              class="field-control min-h-36 resize-y py-2"
              placeholder="[1] 作者. 题名[J]. 期刊, 2020, 1(2): 3-8&#10;[2] 作者. 书名[M]. 出版社, 2021"
            />
          </label>
          <div class="flex items-center justify-between gap-3">
            <p class="text-xs text-stone-500">支持按编号、换行或空行拆分；解析不准时可在右侧编辑。</p>
            <AppButton type="button" :loading="busy" @click="importBulk">导入</AppButton>
          </div>
        </div>
        <div class="border-b border-stone-200 px-5 py-4">
          <h3 class="text-sm font-semibold">{{ editingId ? '编辑文献' : '单条添加' }}</h3>
        </div>
        <form class="grid gap-4 p-5" @submit.prevent="save">
          <label>
            <span class="field-label">作者</span>
            <input v-model="form.authors" class="field-control h-9" placeholder="张三, 李四" />
          </label>
          <label>
            <span class="field-label">题名</span>
            <input v-model="form.title" class="field-control h-9" placeholder="文献标题" />
          </label>
          <label>
            <span class="field-label">出处</span>
            <input v-model="form.source" class="field-control h-9" placeholder="期刊 / 会议 / 出版社 / 网站" />
          </label>
          <label>
            <span class="field-label">年份</span>
            <input v-model="form.year" class="field-control h-9" placeholder="2020" />
          </label>
          <label>
            <span class="field-label">备注</span>
            <input v-model="form.extra" class="field-control h-9" placeholder="卷期页码、链接等" />
          </label>
          <div class="flex gap-2">
            <AppButton type="submit" :loading="busy">{{ editingId ? '保存修改' : '添加' }}</AppButton>
            <AppButton v-if="editingId" variant="secondary" type="button" @click="resetForm">取消</AppButton>
          </div>
        </form>
      </div>
      <div class="panel">
        <div class="flex items-center justify-between border-b border-stone-200 px-5 py-4">
          <h3 class="text-sm font-semibold">已收录</h3>
          <span class="text-xs text-stone-500">{{ items.length }} 条</span>
        </div>
        <ul v-if="items.length" class="divide-y divide-stone-100">
          <li v-for="item in items" :key="item.id" class="px-5 py-4">
            <p class="text-sm text-stone-800">
              {{ item.authors ? `${item.authors}. ` : '' }}{{ item.title }}
              <span v-if="item.source || item.year" class="text-stone-500">
                {{ [item.source, item.year].filter(Boolean).join(', ') }}
              </span>
            </p>
            <p v-if="item.extra" class="mt-1 text-xs text-stone-500">{{ item.extra }}</p>
            <div class="mt-3 flex gap-2">
              <AppButton variant="secondary" @click="edit(item)">编辑</AppButton>
              <AppButton variant="danger" @click="remove(item)">删除</AppButton>
            </div>
          </li>
        </ul>
        <p v-else class="p-5 text-sm text-stone-500">还没有文献。先查找并添加后，再去写作页生成正文。</p>
      </div>
    </div>
  </section>
</template>
