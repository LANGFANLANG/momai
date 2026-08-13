<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppButton from '@/components/ui/AppButton.vue'
import AppField from '@/components/ui/AppField.vue'
import { projectsApi } from '@/api/projects'
import type { ProjectBrief, ProjectBriefUpdate } from '@/types/project'

const projectId = String(useRoute().params.projectId)
const busy = ref(false)
const message = ref('')
const projectTitle = ref('')
const briefId = ref('')
const form = reactive({
  title_explanation: '',
  background: '',
  core_problem: '',
  goal: '',
  significance: '',
  technical_route: '',
  expected_result: '',
  writing_boundary: '',
  modules: '',
  missing_info: '',
  locked_facts: '',
})
type BriefTextField = Exclude<keyof ProjectBriefUpdate, 'modules' | 'missing_info' | 'locked_facts'>
const briefFields: Array<{ key: BriefTextField; label: string }> = [
  { key: 'title_explanation', label: '题目说明' },
  { key: 'background', label: '研究背景' },
  { key: 'core_problem', label: '核心问题' },
  { key: 'goal', label: '研究目标' },
  { key: 'significance', label: '研究意义' },
  { key: 'technical_route', label: '技术路线' },
  { key: 'expected_result', label: '预期成果' },
  { key: 'writing_boundary', label: '写作边界' },
]

function join(values: string[] | null | undefined) {
  return (values ?? []).join('\n')
}
function split(value: string) {
  return value.split(/[，,\n]/).map(item => item.trim()).filter(Boolean)
}
function applyBrief(value: ProjectBrief) {
  briefId.value = value.id
  form.title_explanation = value.title_explanation ?? ''
  form.background = value.background ?? ''
  form.core_problem = value.core_problem ?? ''
  form.goal = value.goal ?? ''
  form.significance = value.significance ?? ''
  form.technical_route = value.technical_route ?? ''
  form.expected_result = value.expected_result ?? ''
  form.writing_boundary = value.writing_boundary ?? ''
  form.modules = join(value.modules)
  form.missing_info = join(value.missing_info)
  form.locked_facts = join(value.locked_facts)
}

async function load() {
  busy.value = true
  try {
    const [project, savedBrief] = await Promise.allSettled([
      projectsApi.get(projectId),
      projectsApi.getBrief(projectId),
    ])
    if (project.status === 'fulfilled') projectTitle.value = project.value.title
    if (savedBrief.status === 'fulfilled') applyBrief(savedBrief.value)
  } catch (error) {
    message.value = error instanceof Error ? error.message : '加载失败'
  } finally {
    busy.value = false
  }
}

async function generate() {
  busy.value = true
  message.value = ''
  try {
    applyBrief(await projectsApi.generateBrief(projectId))
    message.value = 'Brief 已根据项目标题生成，可直接修改后保存'
  } catch (error) {
    message.value = error instanceof Error ? error.message : '生成失败'
  } finally {
    busy.value = false
  }
}

async function saveBrief() {
  if (!briefId.value) {
    message.value = '请先生成 Brief'
    return
  }
  busy.value = true
  message.value = ''
  try {
    const payload: ProjectBriefUpdate = {
      modules: split(form.modules),
      missing_info: split(form.missing_info),
      locked_facts: split(form.locked_facts),
    }
    for (const { key } of briefFields) payload[key] = form[key]
    applyBrief(await projectsApi.updateBrief(projectId, payload))
    message.value = 'Brief 已保存'
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
        <p class="page-kicker">01 / BRIEF</p>
        <h2 class="page-heading">Project Brief</h2>
        <p class="page-copy mt-2">
          根据项目标题「{{ projectTitle || '当前项目' }}」生成写作依据，生成后可直接编辑。
        </p>
      </div>
      <div class="flex gap-2">
        <AppButton variant="secondary" :loading="busy" :disabled="!briefId" @click="saveBrief">
          保存 Brief
        </AppButton>
        <AppButton :loading="busy" @click="generate">生成 Brief</AppButton>
      </div>
    </div>
    <p
      v-if="message"
      class="mb-4 text-sm"
      :class="message.includes('失败') || message.includes('请先') ? 'text-red-700' : 'text-teal-800'"
    >
      {{ message }}
    </p>
    <div class="panel">
      <div class="panel-heading">生成的 Project Brief</div>
      <div class="panel-body grid gap-4 md:grid-cols-2">
        <AppField
          v-for="field in briefFields"
          :key="field.key"
          v-model="form[field.key]"
          :label="field.label"
          textarea
          :rows="4"
        />
        <AppField v-model="form.modules" label="系统模块" textarea :rows="3" />
        <AppField v-model="form.locked_facts" label="锁定事实" textarea :rows="3" />
        <AppField v-model="form.missing_info" label="待补信息" textarea :rows="3" />
      </div>
    </div>
  </section>
</template>
