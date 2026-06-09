<template>
  <aside class="sidebar" aria-label="历史会话">
    <div class="brand-row">
      <div class="brand-mark" aria-hidden="true"></div>
      <div class="brand-name">ReQCollect</div>
    </div>
    <button class="sidebar-action" type="button" @click="$emit('newChat')">
      <span aria-hidden="true">＋</span>
      <span>新对话</span>
    </button>
    <button class="sidebar-action import-btn" type="button" @click="$emit('importDoc')">
      <span aria-hidden="true">📄</span>
      <span>导入记录</span>
    </button>
    <input class="sidebar-search" type="search" placeholder="搜索历史会话" v-model="sessionStore.searchQuery" />
    <div class="history-label">最近</div>
    <div id="session-list">
      <div v-if="sessionStore.filteredSessions.length === 0" class="session-empty">暂无历史会话</div>
      <div
        v-for="s in sessionStore.filteredSessions"
        :key="s.session_id"
        class="session-item"
        :class="{ active: s.session_id === sessionStore.currentId, pinned: s.is_pinned }"
        @click="switchTo(s.session_id)"
      >
        <div class="session-title">
          <span class="name">{{ s.project_name || '未命名项目' }}</span>
          <span class="meta">{{ formatDate(s.updated_at) }} · {{ Math.round((s.sufficiency_score || 0) * 100) }}%</span>
        </div>
      </div>
    </div>
    <div class="sidebar-footer">
      <router-link class="sidebar-link" to="/workspaces">📁 工作空间</router-link>
      <router-link class="sidebar-link" to="/dashboard">📊 数据看板</router-link>
      <a class="sidebar-link" href="/docs">API 文档</a>
      <a class="sidebar-link" href="/api/health">服务状态</a>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useSessionStore } from '@/stores/session'
import { useRouter } from 'vue-router'

const sessionStore = useSessionStore()
const router = useRouter()

function formatDate(dateStr: string) {
  if (!dateStr) return '刚刚'
  try { return new Date(dateStr).toLocaleDateString() } catch { return '刚刚' }
}

function switchTo(sid: string) {
  sessionStore.setCurrent(sid)
  router.push(`/chat/${sid}`)
}

defineEmits<{ newChat: [], importDoc: [] }>()
</script>
