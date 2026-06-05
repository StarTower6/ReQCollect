<template>
  <div class="profile-section">
    <div class="profile-section-title">需求完整度</div>
    <div style="display:flex;justify-content:center;padding:16px 0">
      <svg width="120" height="120" viewBox="0 0 120 120">
        <circle class="sufficiency-ring-bg" cx="60" cy="60" r="48" style="fill:none;stroke:#eef3fb;stroke-width:8"/>
        <circle class="sufficiency-ring-fg" cx="60" cy="60" r="48"
                :style="{ strokeDasharray: circumference, strokeDashoffset: offset, fill: 'none', stroke: 'var(--brand)', strokeWidth: 8, strokeLinecap: 'round', transition: 'stroke-dashoffset 0.6s ease' }"
                transform="rotate(-90, 60, 60)"/>
        <text x="60" y="56" text-anchor="middle" style="font-size:22px;font-weight:800;fill:#202634">{{ percent }}%</text>
        <text x="60" y="74" text-anchor="middle" style="font-size:11px;fill:var(--muted-light)">完整度</text>
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ percent: number }>()
const circumference = 2 * Math.PI * 48
const offset = computed(() => circumference * (1 - Math.min(props.percent, 100) / 100))
</script>
