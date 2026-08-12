<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'

const navigation = [
  { label: '项目', to: '/projects' },
]
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-900">
    <header class="border-b border-slate-200 bg-white">
      <div class="mx-auto flex h-14 max-w-7xl items-center gap-8 px-6">
        <RouterLink class="text-lg font-semibold" to="/projects">墨脉</RouterLink>
        <nav class="flex items-center gap-4 text-sm text-slate-600">
          <RouterLink
            v-for="item in navigation"
            :key="item.to"
            :to="item.to"
            class="transition hover:text-slate-950"
          >
            {{ item.label }}
          </RouterLink>
        </nav>
      </div>
    </header>
    <main class="mx-auto max-w-7xl px-6 py-8">
      <RouterView />
    </main>
  </div>
</template>
