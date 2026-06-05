<template>
  <div>
    <SufficiencyRing :percent="percent" />

    <div class="profile-section">
      <div class="profile-section-title">画像字段</div>
      <div v-for="field in sortedFields" :key="field.key" class="field-item"
           :class="{ filled: field.filled, empty: !field.filled }"
           @click="field.filled && (field.expanded = !field.expanded)">
        <span class="field-dot" :class="{ filled: field.filled, empty: !field.filled }"></span>
        <span class="field-name">{{ field.label }}</span>
        <span v-if="field.filled" class="field-arrow" :class="{ open: field.expanded }">▼</span>
        <span class="field-weight">×{{ field.weight }}</span>
        <div v-if="field.expanded && field.filled" class="field-detail">
          {{ formatValue(field.raw) }}
        </div>
      </div>
    </div>

    <div class="profile-section">
      <div class="profile-section-title">待补充</div>
      <div class="missing-guide" v-if="missingFields.length">
        <span style="font-size:16px;margin-right:6px">💡</span>建议优先补充：
        <ul style="margin:6px 0 0 16px"><li v-for="f in missingFields" :key="f.key" style="margin:3px 0">{{ f.label }}</li></ul>
      </div>
      <div class="missing-guide" v-else style="background:#e8f5e9;color:#2e7d32">✅ 所有字段已填写完毕！</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import type { RequirementProfile } from '@/types'
import { FIELDS_CONFIG } from '@/types'
import SufficiencyRing from './SufficiencyRing.vue'

const props = defineProps<{ profile: RequirementProfile; percent: number }>()

function isFilled(v: any): boolean {
  if (v === null || v === undefined) return false
  if (typeof v === 'string') return v.trim().length > 0
  if (Array.isArray(v)) return v.length > 0
  if (typeof v === 'number') return v > 0
  if (typeof v === 'object') return Object.keys(v).length > 0
  return true
}

function formatValue(v: any): string {
  if (!v) return '—'
  if (typeof v === 'string') return v.length > 200 ? v.slice(0, 200) + '...' : v
  if (Array.isArray(v)) return v.map(i => typeof i === 'object' ? (i.name || i.role || i.module || JSON.stringify(i)) : String(i)).join('、')
  if (typeof v === 'object') return Object.keys(v).map(k => `${k}: ${v[k]}`).join('；')
  return String(v)
}

const fields = computed(() =>
  FIELDS_CONFIG.map(f => ({
    ...f,
    raw: (props.profile as any)[f.key],
    filled: isFilled((props.profile as any)[f.key]),
    expanded: false,
  }))
)

const sortedFields = computed(() =>
  [...fields.value].sort((a, b) => {
    if (a.filled !== b.filled) return a.filled ? 1 : -1
    return b.weight - a.weight
  })
)

const missingFields = computed(() => sortedFields.value.filter(f => !f.filled))
</script>
