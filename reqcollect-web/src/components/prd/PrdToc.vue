<template>
  <div class="prd-toc">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px">
      <router-link to="/chat" class="sidebar-link" style="display:inline-flex">← 返回对话</router-link>
    </div>
    <div class="profile-section-title">目录</div>
    <a v-for="(sec, i) in sections" :key="i" class="prd-toc-item" :href="`#section-${i}`"
       :style="{ fontWeight: activeIndex === i ? 720 : 400 }"
       @click.prevent="$emit('scrollTo', i)">
      {{ i + 1 }}. {{ sec.title }}
    </a>
    <div style="margin-top:16px">
      <button class="tool-btn" type="button" @click="$emit('download')">📥 下载 Markdown</button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ sections: any[]; activeIndex: number }>()
defineEmits<{ scrollTo: [index: number]; download: [] }>()
</script>
