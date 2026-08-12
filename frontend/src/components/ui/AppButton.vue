<script setup lang="ts">
import { computed } from 'vue'
const props = withDefaults(defineProps<{ variant?: 'primary' | 'secondary' | 'danger'; loading?: boolean; disabled?: boolean; type?: 'button' | 'submit' }>(), { variant: 'primary', type: 'button', loading: false, disabled: false })
const classes = computed(() => ({ primary: 'border-teal-800 bg-teal-800 text-white hover:bg-teal-900', secondary: 'border-stone-300 bg-white text-stone-700 hover:border-stone-500 hover:bg-stone-50', danger: 'border-red-200 bg-white text-red-700 hover:bg-red-50' }[props.variant]))
</script>
<template><button :type="type" :disabled="loading || disabled" class="inline-flex h-9 items-center justify-center border px-3 text-sm font-medium transition disabled:cursor-wait disabled:opacity-60" :class="classes"><span v-if="loading" class="mr-2 h-3 w-3 animate-spin rounded-full border-2 border-current border-r-transparent" /><slot /></button></template>
