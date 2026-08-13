<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowRight, ExternalLink, Plus, Presentation, Sparkles, Trash2 } from 'lucide-vue-next'
import AppButton from '@/components/ui/AppButton.vue'
import { useProjectStore } from '@/stores/project'
import type { ProjectStatus, ProjectType } from '@/types/project'

const store = useProjectStore()
const error = ref('')

const types: Record<ProjectType, string> = {
  course_report: '课程报告',
  thesis: '毕业论文',
  proposal: '开题报告',
}

const statuses: Record<ProjectStatus, string> = {
  drafting_info: '信息收集',
  brief_ready: 'Brief 已就绪',
  outline_ready: '大纲已就绪',
  relations_ready: '关系已就绪',
  drafting_chapters: '写作中',
  review_ready: '待校验',
  export_ready: '可导出',
}

const resourceGroups = [
  {
    title: 'AI coding skills',
    subtitle: 'build-and-ship 工作流与发布实践',
    icon: Sparkles,
    links: [
      { label: 'Gitee', href: 'https://gitee.com/langfanlang/build-and-ship' },
      { label: 'GitHub', href: 'https://github.com/LANGFANLANG/build-and-ship' },
    ],
  },
  {
    title: 'PPT AI 生成工具',
    subtitle: 'Presenton 下载与 ppt-master skills',
    icon: Presentation,
    links: [
      { label: 'Presenton', href: 'https://presenton.ai/download' },
      { label: 'ppt-master', href: 'https://github.com/hugohe3/ppt-master' },
    ],
  },
]

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

async function removeProject(id: string) {
  if (!window.confirm('删除该项目及其写作内容？')) return

  try {
    await store.deleteProject(id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  }
}

onMounted(async () => {
  try {
    await store.loadProjects()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '项目加载失败'
  }
})
</script>

<template>
  <section>
    <div class="mb-5 flex items-start justify-between gap-4">
      <div>
        <p class="page-kicker">PROJECTS</p>
        <h1 class="page-heading">写作项目</h1>
        <p class="page-copy mt-2">从一个明确的问题出发，逐步完成结构、章节与校验。</p>
      </div>
      <RouterLink to="/projects/new">
        <AppButton>
          <Plus :size="16" class="mr-1.5" />
          新建项目
        </AppButton>
      </RouterLink>
    </div>

    <div class="mb-7 grid gap-3 lg:grid-cols-2">
      <div
        v-for="group in resourceGroups"
        :key="group.title"
        class="border border-teal-800 bg-white px-5 py-4 shadow-[4px_4px_0_0_#115e59]"
      >
        <div class="flex h-full flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div class="flex items-start gap-3">
            <span class="mt-0.5 grid h-8 w-8 shrink-0 place-items-center bg-teal-800 text-white">
              <component :is="group.icon" :size="17" />
            </span>
            <div>
              <p class="text-sm font-semibold text-stone-900">{{ group.title }}</p>
              <p class="mt-1 text-xs leading-5 text-stone-600">{{ group.subtitle }}</p>
            </div>
          </div>
          <div class="flex shrink-0 flex-wrap gap-2">
            <a
              v-for="link in group.links"
              :key="link.href"
              :href="link.href"
              target="_blank"
              rel="noreferrer"
              class="inline-flex h-9 items-center gap-1.5 border border-teal-800 bg-teal-800 px-3 text-sm font-medium text-white transition hover:bg-teal-900"
              :title="`打开 ${link.label} 资源`"
            >
              {{ link.label }}
              <ExternalLink :size="14" />
            </a>
          </div>
        </div>
      </div>
    </div>

    <p v-if="error" class="mb-4 border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {{ error }}
    </p>

    <div v-if="store.loading" class="panel p-8 text-sm text-stone-500">正在读取项目...</div>

    <div v-else-if="!store.projects.length" class="border-y border-stone-200 py-14 text-center">
      <p class="text-lg font-semibold text-stone-800">还没有写作项目</p>
      <p class="mt-2 text-sm text-stone-500">创建第一个项目，开始整理你的研究材料。</p>
    </div>

    <div v-else class="grid gap-3">
      <article
        v-for="project in store.projects"
        :key="project.id"
        class="panel flex min-w-0 items-center gap-5 p-5 transition hover:border-teal-700"
      >
        <div class="min-w-0 flex-1">
          <div class="mb-2 flex flex-wrap items-center gap-2">
            <span class="border border-stone-300 px-2 py-0.5 text-xs text-stone-600">
              {{ types[project.type] }}
            </span>
            <span class="text-xs text-teal-800">{{ statuses[project.status] }}</span>
          </div>
          <h2 class="truncate text-lg font-semibold text-stone-900">{{ project.title }}</h2>
          <p class="mt-1 text-sm text-stone-500">
            {{ project.major || '未填写专业' }}
            <span class="mx-1">·</span>
            更新于 {{ formatDate(project.updated_at) }}
          </p>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <RouterLink :to="`/projects/${project.id}/brief`">
            <AppButton variant="secondary">
              <span class="hidden sm:inline">打开</span>
              <ArrowRight :size="16" class="sm:ml-1.5" />
            </AppButton>
          </RouterLink>
          <button
            class="grid h-9 w-9 place-items-center border border-transparent text-stone-400 hover:border-red-200 hover:text-red-700"
            title="删除项目"
            @click="removeProject(project.id)"
          >
            <Trash2 :size="16" />
          </button>
        </div>
      </article>
    </div>
  </section>
</template>
