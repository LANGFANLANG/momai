<script setup lang="ts">
defineProps<{ label: string; hint?: string; textarea?: boolean; rows?: number }>()
const model = defineModel<string | number | null>()
</script>
<template><label class="block"><span class="field-label">{{ label }}</span><textarea v-if="textarea" v-model="model" class="field-control min-h-24" :rows="rows ?? 4" /><input v-else v-model="model" class="field-control h-9" /><span v-if="hint" class="mt-1 block text-xs text-stone-500">{{ hint }}</span></label></template>
