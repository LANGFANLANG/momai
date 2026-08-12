<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="min-h-screen bg-[#f6f5f1] text-stone-900">
    <header class="border-b border-stone-200 bg-[#fbfaf7]">
      <div class="mx-auto flex h-14 max-w-[1440px] items-center px-6">
        <RouterLink class="text-lg font-semibold tracking-[0.12em] text-teal-800" to="/projects">墨脉</RouterLink>
        <span class="ml-4 border-l border-stone-300 pl-4 text-xs tracking-wide text-stone-500">学术写作工作台</span>
      </div>
    </header>
    <main class="mx-auto max-w-[1440px] px-6 py-7"><RouterView /></main>
  </div>
</template>
