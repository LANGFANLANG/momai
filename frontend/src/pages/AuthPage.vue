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
const captchaImage = ref('')
const captchaAnswer = ref('')
const error = ref('')

const title = computed(() => (mode.value === 'login' ? '登录账号' : '注册账号'))
const submitText = computed(() => (mode.value === 'login' ? '登录' : '注册并登录'))

async function refreshCaptcha() {
  const captcha = await authApi.captcha()
  captchaId.value = captcha.id
  captchaImage.value = captcha.image
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
  <main class="auth-page">
    <section class="auth-intro">
      <div class="auth-brand">
        <span class="auth-brand-mark">墨</span>
        <span>墨脉</span>
      </div>
      <div class="auth-intro-copy">
        <p class="auth-kicker">ACADEMIC WORKSPACE</p>
        <h1>把思路写清楚，<br /><em>让论证自然成形。</em></h1>
        <p>从研究简报、章节结构到一致性检查，把一篇论文需要的工作收在同一个安静的空间里。</p>
      </div>
      <div class="auth-intro-foot">
        <span>01</span>
        <span class="auth-rule" />
        <span>专注于写作本身</span>
      </div>
    </section>

    <section class="auth-form-side">
      <div class="auth-form-wrap">
        <div class="auth-form-heading">
          <p class="auth-kicker">ACCOUNT</p>
          <h2>{{ title }}</h2>
          <p>{{ mode === 'login' ? '登录后继续你的研究项目。' : '创建账号，开始整理你的研究。' }}</p>
        </div>

        <form class="auth-form" @submit.prevent="submit">
          <label class="auth-field">
            <span>用户名</span>
            <input v-model="username" autocomplete="username" placeholder="输入用户名" />
          </label>
          <label class="auth-field">
            <span>密码</span>
            <input v-model="password" type="password" autocomplete="current-password" placeholder="输入密码" />
          </label>
          <label class="auth-field">
            <span>验证码</span>
            <div class="auth-captcha-row">
              <input v-model="captchaAnswer" placeholder="输入图片中的字符" autocomplete="off" />
              <button class="auth-captcha" title="点击刷新验证码" type="button" @click="refreshCaptcha">
                <img v-if="captchaImage" :src="captchaImage" alt="验证码图片，点击刷新" />
                <span v-else>加载中</span>
              </button>
            </div>
          </label>
          <p v-if="error" class="auth-error">{{ error }}</p>
          <AppButton class="auth-submit" type="submit" :loading="auth.loading">{{ submitText }}</AppButton>
        </form>

        <button class="auth-switch" type="button" @click="mode = mode === 'login' ? 'register' : 'login'; error = ''">
          {{ mode === 'login' ? '还没有账号？注册新账号' : '已经有账号？返回登录' }}
        </button>
        <p class="auth-note">默认账号：admin / admin</p>
      </div>
    </section>
  </main>
</template>

<style scoped>
.auth-page {
  display: grid;
  min-height: 100dvh;
  grid-template-columns: minmax(320px, 0.9fr) minmax(420px, 1.1fr);
}

.auth-intro {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: clamp(2rem, 6vw, 6rem);
  color: #f5f1e8;
  background: #164e4a;
  background-image: linear-gradient(135deg, rgba(11, 61, 57, 0.4), transparent 55%), repeating-linear-gradient(115deg, transparent 0 32px, rgba(245, 241, 232, 0.055) 33px, transparent 34px 72px);
}

.auth-brand { display: flex; align-items: center; gap: 0.75rem; font-size: 1.15rem; font-weight: 600; letter-spacing: 0.16em; }
.auth-brand-mark { display: grid; width: 2.25rem; height: 2.25rem; place-items: center; border: 1px solid rgba(245, 241, 232, 0.55); font-family: serif; font-size: 1.25rem; letter-spacing: 0; }
.auth-intro-copy { max-width: 30rem; margin: auto 0; }
.auth-kicker { margin: 0 0 1rem; color: #9fd0c4; font-size: 0.68rem; font-weight: 600; letter-spacing: 0.2em; }
.auth-intro h1 { margin: 0; font-family: Georgia, "Songti SC", serif; font-size: clamp(2.4rem, 4.7vw, 5rem); font-weight: 400; line-height: 1.08; letter-spacing: -0.04em; }
.auth-intro h1 em { color: #d0e6dc; font-style: normal; }
.auth-intro-copy > p:last-child { max-width: 28rem; margin: 2rem 0 0; color: #c2d9d0; font-size: 0.92rem; line-height: 1.9; }
.auth-intro-foot { display: flex; align-items: center; gap: 0.75rem; color: #9fc8be; font-size: 0.7rem; letter-spacing: 0.12em; }
.auth-rule { width: 3rem; height: 1px; background: #79aca0; }
.auth-form-side { display: grid; place-items: center; padding: clamp(2rem, 6vw, 6rem); background: #f1f0eb; }
.auth-form-wrap { width: min(100%, 27rem); }
.auth-form-heading { margin-bottom: 2.6rem; }
.auth-form-heading .auth-kicker { color: #78716c; }
.auth-form-heading h2 { margin: 0; color: #292524; font-family: Georgia, "Songti SC", serif; font-size: clamp(2.1rem, 4vw, 3.3rem); font-weight: 400; letter-spacing: -0.045em; }
.auth-form-heading p:last-child { margin: 0.8rem 0 0; color: #78716c; font-size: 0.9rem; }
.auth-form { display: grid; gap: 1.25rem; }
.auth-field { display: grid; gap: 0.5rem; }
.auth-field > span { color: #57534e; font-size: 0.75rem; font-weight: 600; }
.auth-field input { width: 100%; box-sizing: border-box; border: 0; border-bottom: 1px solid #cfcac2; background: transparent; padding: 0.8rem 0; color: #292524; outline: none; transition: border-color 180ms ease, box-shadow 180ms ease; }
.auth-field input::placeholder { color: #a8a29e; }
.auth-field input:focus { border-color: #0f766e; box-shadow: 0 1px 0 #0f766e; }
.auth-captcha-row { display: grid; grid-template-columns: minmax(0, 1fr) 9rem; gap: 0.75rem; }
.auth-captcha { height: 2.75rem; overflow: hidden; border: 1px solid #d6d3d1; background: #e7e5e4; cursor: pointer; }
.auth-captcha img { display: block; width: 100%; height: 100%; object-fit: cover; }
.auth-captcha span { color: #78716c; font-size: 0.75rem; }
.auth-submit { width: 100%; height: 3rem; margin-top: 0.5rem; border-color: #115e59 !important; background: #115e59 !important; font-size: 0.85rem; letter-spacing: 0.08em; }
.auth-submit:hover { background: #0f4f4b !important; }
.auth-switch { margin-top: 2rem; padding: 0; border: 0; background: transparent; color: #0f766e; cursor: pointer; font-size: 0.82rem; }
.auth-switch:hover { color: #134e4a; text-decoration: underline; text-underline-offset: 0.25rem; }
.auth-note { margin-top: 3.5rem; color: #a8a29e; font-size: 0.72rem; }
.auth-error { margin: 0; border-left: 2px solid #b91c1c; padding: 0.65rem 0.8rem; background: #fef2f2; color: #991b1b; font-size: 0.78rem; line-height: 1.5; }

@media (max-width: 760px) {
  .auth-page { display: block; }
  .auth-intro { min-height: 16rem; padding: 1.75rem; }
  .auth-intro-copy { margin: 3.5rem 0 1rem; }
  .auth-intro h1 { font-size: 2.6rem; }
  .auth-intro-copy > p:last-child, .auth-intro-foot { display: none; }
  .auth-form-side { min-height: calc(100dvh - 16rem); padding: 2.5rem 1.75rem 3rem; }
}
</style>
