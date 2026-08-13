<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppButton from '@/components/ui/AppButton.vue'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const mode = ref<'login' | 'register'>('login')
const username = ref('admin')
const password = ref('')
const captchaId = ref('')
const captchaCode = ref('')
const captchaAnswer = ref('')
const error = ref('')

const title = computed(() => (mode.value === 'login' ? '登录账号' : '注册账号'))
const submitText = computed(() => (mode.value === 'login' ? '登录' : '注册并登录'))

async function refreshCaptcha() {
  const captcha = await authApi.captcha()
  captchaId.value = captcha.id
  captchaCode.value = captcha.code
  captchaAnswer.value = ''
}

async function submit() {
  if (!username.value.trim() || !password.value || !captchaAnswer.value.trim()) {
    error.value = '请填写用户名、密码和验证码'
    return
  }
  error.value = ''
  try {
    const payload = {
      username: username.value.trim(),
      password: password.value,
      captcha_id: captchaId.value,
      captcha_answer: captchaAnswer.value.trim(),
    }
    if (mode.value === 'login') {
      await auth.login(payload)
    } else {
      await auth.register(payload)
    }
    await router.push('/projects')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
    await refreshCaptcha()
  }
}

onMounted(() => {
  refreshCaptcha().catch(e => {
    error.value = e instanceof Error ? e.message : '验证码加载失败'
  })
})
</script>

<template>
  <section class="mx-auto max-w-md">
    <div class="mb-7">
      <p class="page-kicker">ACCOUNT</p>
      <h1 class="page-heading">{{ title }}</h1>
      <p class="page-copy mt-2">默认账号为 admin，当前已有项目归属在 admin 下。</p>
    </div>
    <form class="panel" @submit.prevent="submit">
      <div class="panel-body grid gap-4">
        <label>
          <span class="field-label">用户名</span>
          <input v-model="username" class="field-control h-9" autocomplete="username" />
        </label>
        <label>
          <span class="field-label">密码</span>
          <input v-model="password" class="field-control h-9" type="password" autocomplete="current-password" />
        </label>
        <label>
          <span class="field-label">验证码</span>
          <div class="grid gap-2 sm:grid-cols-[1fr_9rem]">
            <input v-model="captchaAnswer" class="field-control h-9" placeholder="输入右侧验证码" autocomplete="off" />
            <button
              class="flex h-9 items-center justify-center border border-stone-300 bg-stone-100 px-3 font-mono text-lg tracking-[0.18em] text-stone-800 hover:border-teal-700"
              title="点击刷新验证码"
              type="button"
              @click="refreshCaptcha"
            >
              {{ captchaCode || '刷新' }}
            </button>
          </div>
        </label>
      </div>
      <div class="flex items-center justify-between border-t border-stone-200 px-5 py-4">
        <button
          class="text-sm text-teal-800 hover:text-teal-950"
          type="button"
          @click="mode = mode === 'login' ? 'register' : 'login'; error = ''"
        >
          {{ mode === 'login' ? '注册新账号' : '返回登录' }}
        </button>
        <AppButton type="submit" :loading="auth.loading">{{ submitText }}</AppButton>
      </div>
    </form>
    <p v-if="error" class="mt-4 border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{{ error }}</p>
  </section>
</template>
