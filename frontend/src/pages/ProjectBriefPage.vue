<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppButton from '@/components/ui/AppButton.vue'
import AppField from '@/components/ui/AppField.vue'
import { projectsApi } from '@/api/projects'
import type {
  ProjectBrief,
  ProjectBriefUpdate,
  ProjectContext,
  ProjectContextPayload,
} from '@/types/project'

const projectId = String(useRoute().params.projectId)
const busy = ref(false)
const message = ref('')
const brief = ref<ProjectBrief | null>(null)
const briefLists = reactive({ modules: '', missing_info: '', locked_facts: '' })
const form = reactive<Record<string, string>>({
  background: '', problem: '', goal: '', scenario: '', target_users: '', technologies: '',
  modules: '', architecture: '', environment: '', experiments: '', writing_preferences: '',
})
const labels: Record<string, string> = {
  background: '研究背景', problem: '核心问题', goal: '研究目标', scenario: '应用场景',
  target_users: '目标用户', technologies: '技术与方法', modules: '系统模块', architecture: '整体架构',
  environment: '实验环境', experiments: '实验设计', writing_preferences: '写作偏好',
}
type BriefTextField = Exclude<keyof ProjectBriefUpdate, 'modules' | 'missing_info' | 'locked_facts'>

const briefFields: Array<{ key: BriefTextField; label: string }> = [
  { key: 'title_explanation', label: '题目说明' },
  { key: 'background', label: 'Brief 背景' },
  { key: 'core_problem', label: '核心问题' },
  { key: 'goal', label: '研究目标' },
  { key: 'significance', label: '研究意义' },
  { key: 'technical_route', label: '技术路线' },
  { key: 'expected_result', label: '预期成果' },
  { key: 'writing_boundary', label: '写作边界' },
]

function join(values: string[] | null | undefined) { return (values ?? []).join('\n') }
function split(value: string) { return value.split(/[，,\n]/).map(item => item.trim()).filter(Boolean) }
function applyBrief(value: ProjectBrief) {
  brief.value = value
  briefLists.modules = join(value.modules)
  briefLists.missing_info = join(value.missing_info)
  briefLists.locked_facts = join(value.locked_facts)
}
function applyContext(context: ProjectContext) {
  form.background = context.background ?? ''
  form.problem = context.problem ?? ''
  form.goal = context.goal ?? ''
  form.scenario = context.scenario ?? ''
  form.target_users = context.target_users ?? ''
  form.technologies = join(context.technologies)
  form.modules = join(context.modules)
  form.architecture = context.architecture ?? ''
  form.environment = context.environment ?? ''
  form.experiments = context.experiments ?? ''
  form.writing_preferences = String(context.writing_prefs?.notes ?? '')
}
function payload(): ProjectContextPayload {
  return {
    background: form.background, problem: form.problem, goal: form.goal, scenario: form.scenario,
    target_users: form.target_users, technologies: split(form.technologies), modules: split(form.modules),
    architecture: form.architecture, environment: form.environment, experiments: form.experiments,
    writing_prefs: form.writing_preferences ? { notes: form.writing_preferences } : null,
  }
}
async function load() {
  busy.value = true
  try {
    const [context, savedBrief] = await Promise.allSettled([
      projectsApi.getContext(projectId),
      projectsApi.getBrief(projectId),
    ])
    if (context.status === 'fulfilled') applyContext(context.value)
    if (savedBrief.status === 'fulfilled') applyBrief(savedBrief.value)
  } catch (error) {
    message.value = error instanceof Error ? error.message : '加载失败'
  } finally {
    busy.value = false
  }
}
async function save(): Promise<boolean> {
  busy.value = true
  message.value = ''
  try {
    await projectsApi.saveContext(projectId, payload())
    message.value = '上下文已保存'
    return true
  } catch (error) {
    message.value = error instanceof Error ? error.message : '保存失败'
    return false
  } finally {
    busy.value = false
  }
}
async function generate() {
  if (!await save()) return
  busy.value = true
  try {
    applyBrief(await projectsApi.generateBrief(projectId))
    message.value = 'Brief 已生成'
  } catch (error) {
    message.value = error instanceof Error ? error.message : '生成失败'
  } finally {
    busy.value = false
  }
}
async function saveBrief() {
  if (!brief.value) return
  busy.value = true
  message.value = ''
  try {
    const payload: ProjectBriefUpdate = {}
    for (const { key } of briefFields) payload[key] = brief.value[key]
    payload.modules = split(briefLists.modules)
    payload.missing_info = split(briefLists.missing_info)
    payload.locked_facts = split(briefLists.locked_facts)
    applyBrief(await projectsApi.updateBrief(projectId, payload))
    message.value = 'Brief 已保存'
  } catch (error) {
    message.value = error instanceof Error ? error.message : 'Brief 保存失败'
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
        <h2 class="page-heading">研究上下文</h2>
        <p class="page-copy mt-2">把已知条件写清楚，生成结果会更稳定。</p>
      </div>
      <div class="flex gap-2">
        <AppButton variant="secondary" :loading="busy" @click="save">保存上下文</AppButton>
        <AppButton :loading="busy" @click="generate">生成 Brief</AppButton>
      </div>
    </div>
    <p v-if="message" class="mb-4 text-sm" :class="message.includes('失败') ? 'text-red-700' : 'text-teal-800'">{{ message }}</p>
    <div class="grid gap-4 xl:grid-cols-2">
      <div class="panel">
        <div class="panel-heading">研究设定</div>
        <div class="panel-body grid gap-4">
          <AppField
            v-for="key in ['background', 'problem', 'goal', 'scenario', 'target_users']"
            :key="key"
            v-model="form[key]"
            :label="labels[key]"
            textarea
            :rows="3"
          />
        </div>
      </div>
      <div class="panel">
        <div class="panel-heading">方案与写作约束</div>
        <div class="panel-body grid gap-4">
          <AppField
            v-for="key in ['technologies', 'modules', 'architecture', 'environment', 'experiments', 'writing_preferences']"
            :key="key"
            v-model="form[key]"
            :label="labels[key]"
            textarea
            :rows="3"
          />
        </div>
      </div>
    </div>
    <div v-if="brief" class="panel mt-4">
      <div class="panel-heading flex items-center justify-between gap-3">
        <span>生成的 Project Brief</span>
        <AppButton variant="secondary" :loading="busy" @click="saveBrief">保存 Brief</AppButton>
      </div>
      <div class="panel-body grid gap-4 md:grid-cols-2">
        <AppField
          v-for="field in briefFields"
          :key="field.key"
          v-model="brief[field.key]"
          :label="field.label"
          textarea
          :rows="3"
        />
        <AppField v-model="briefLists.modules" label="系统模块" textarea :rows="3" />
        <AppField v-model="briefLists.locked_facts" label="锁定事实" textarea :rows="3" />
        <AppField v-model="briefLists.missing_info" label="待补信息" textarea :rows="3" />
      </div>
    </div>
  </section>
</template>
