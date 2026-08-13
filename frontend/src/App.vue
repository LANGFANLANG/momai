<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { useRouter } from 'vue-router'
import AppButton from '@/components/ui/AppButton.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

async function logout() {
  auth.logout()
  await router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-[#f6f5f1] text-stone-900">
    <header class="border-b border-stone-200 bg-[#fbfaf7]">
      <div class="mx-auto flex h-14 max-w-[1440px] items-center px-6">
        <RouterLink class="text-lg font-semibold tracking-[0.12em] text-teal-800" to="/projects">墨脉</RouterLink>
        <span class="ml-4 border-l border-stone-300 pl-4 text-xs tracking-wide text-stone-500">学术写作工作台</span>
        <div v-if="auth.user" class="ml-auto flex items-center gap-3">
          <span class="text-xs text-stone-500">{{ auth.user.username }}</span>
          <AppButton variant="secondary" type="button" @click="logout">退出</AppButton>
        </div>
      </div>
    </header>
    <main class="mx-auto max-w-[1440px] px-6 py-7"><RouterView /></main>
  </div>
</template>
