<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { BookMarked, Download, FileText, GitBranch, ListTree, PenLine, ScanSearch } from 'lucide-vue-next'
import { useProjectStore } from '@/stores/project'
const route = useRoute(); const store = useProjectStore(); const error = ref(''); const projectId = computed(() => String(route.params.projectId))
const items = computed(() => [
  { label: 'Brief', icon: FileText, to: `/projects/${projectId.value}/brief` },
  { label: '大纲', icon: ListTree, to: `/projects/${projectId.value}/outline` },
  { label: '章节关系', icon: GitBranch, to: `/projects/${projectId.value}/relations` },
  { label: '参考文献', icon: BookMarked, to: `/projects/${projectId.value}/references` },
  { label: '写作', icon: PenLine, to: `/projects/${projectId.value}/chapters` },
  { label: '一致性校验', icon: ScanSearch, to: `/projects/${projectId.value}/review` },
  { label: '导出', icon: Download, to: `/projects/${projectId.value}/export` },
])
onMounted(async () => { try { await store.loadProject(projectId.value) } catch (e) { error.value = e instanceof Error ? e.message : '项目加载失败' } })
</script>
<template><div v-if="error" class="border border-red-200 bg-red-50 p-4 text-sm text-red-700">{{ error }}</div><div v-else class="grid gap-7 lg:grid-cols-[190px_minmax(0,1fr)]"><aside class="lg:border-r lg:border-stone-200 lg:pr-5"><RouterLink to="/projects" class="mb-6 inline-block text-xs text-stone-500 hover:text-teal-800">← 全部项目</RouterLink><p class="mb-1 text-xs text-stone-500">当前项目</p><h1 class="mb-6 line-clamp-2 text-sm font-semibold leading-6 text-stone-900">{{ store.currentProject?.title || '正在加载…' }}</h1><nav class="flex gap-1 overflow-x-auto lg:flex-col"><RouterLink v-for="item in items" :key="item.label" :to="item.to" class="flex shrink-0 items-center gap-2 border-l-2 border-transparent px-2 py-2 text-sm text-stone-600 transition hover:bg-stone-100 hover:text-stone-900" active-class="!border-teal-800 !bg-teal-50 !text-teal-900"><component :is="item.icon" :size="15" />{{ item.label }}</RouterLink></nav></aside><RouterView /></div></template>
