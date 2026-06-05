<template>
  <div v-if="replies.length" class="quick-replies" :class="{ 'multi-select': mode === 'multi' }">
    <button
      v-for="qr in replies"
      :key="qr.value"
      class="quick-reply-btn"
      :class="{ selected: selectedSet.has(qr.value) }"
      :disabled="disabled"
      @click="handleClick(qr)"
    >
      {{ qr.label }}
    </button>
    <div v-if="mode === 'multi'" class="quick-reply-actions">
      <button class="quick-reply-submit" :disabled="selectedSet.size === 0" @click="$emit('submit', getSelection())">
        确认选择
      </button>
      <button class="quick-reply-clear" @click="clearAll">清空</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { QrOption } from '@/types'

const props = defineProps<{
  replies: QrOption[]
  mode: 'single' | 'multi'
  disabled: boolean
}>()

const emit = defineEmits<{
  select: [value: string]
  submit: [value: string]
}>()

const selectedSet = ref<Set<string>>(new Set())

watch(() => props.disabled, (v) => { if (v) selectedSet.value = new Set() })

function handleClick(qr: QrOption) {
  if (props.disabled) return
  if (props.mode === 'multi') {
    const s = new Set(selectedSet.value)
    if (s.has(qr.value)) { s.delete(qr.value) } else { s.add(qr.value) }
    selectedSet.value = s
    return
  }
  emit('select', qr.value)
}

function getSelection() {
  return Array.from(selectedSet.value).join('、')
}

function clearAll() {
  selectedSet.value = new Set()
}
</script>
