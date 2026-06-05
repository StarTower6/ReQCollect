<template>
  <header class="topbar">
    <div style="display:flex;gap:8px;justify-self:start">
      <router-link to="/dashboard" class="tool-btn" style="text-decoration:none">📊</router-link>
      <router-link :to="prdLink" class="tool-btn" style="text-decoration:none" v-if="sessionId">📄 PRD</router-link>
    </div>
    <div class="topbar-title">{{ title }}</div>
    <div class="topbar-actions">
      <span class="status-chip">完整度 {{ sufficiencyPercent }}%</span>
      <span class="status-chip">{{ sessionId ? '进行中' : '未开始' }}</span>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title: string
  sessionId: string | null
  sufficiencyPercent: number
}>()

const prdLink = computed(() => props.sessionId ? `/prd/${props.sessionId}` : '#')
</script>
