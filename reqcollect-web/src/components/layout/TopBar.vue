<template>
  <header class="topbar">
    <div style="display:flex;gap:8px;justify-self:start">
      <router-link to="/dashboard" class="tool-btn" style="text-decoration:none">📊</router-link>
      <router-link :to="prdLink" class="tool-btn" style="text-decoration:none" v-if="sessionId">📄 PRD</router-link>
    </div>
    <div class="topbar-title">{{ title }}</div>
    <div class="topbar-actions">
      <span class="status-chip clickable" @click="$emit('showProfile')" style="cursor:pointer">完整度 {{ sufficiencyPercent }}%</span>
      <span class="status-chip">{{ sessionId ? '进行中' : '未开始' }}</span>
      <el-dropdown trigger="click" class="user-dropdown">
        <span class="user-trigger">
          <el-avatar :size="28" icon="UserFilled" />
          <span class="user-name">{{ user?.display_name || user?.username }}</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item v-if="isAdmin">
              <router-link to="/admin/users" style="text-decoration:none;color:inherit">用户管理</router-link>
            </el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { UserFilled } from '@element-plus/icons-vue'

const emit = defineEmits<{
  showProfile: []
}>()

const props = defineProps<{
  title: string
  sessionId: string | null
  sufficiencyPercent: number
}>()

const router = useRouter()
const authStore = useAuthStore()
const user = computed(() => authStore.user)
const isAdmin = computed(() => authStore.isAdmin)

const prdLink = computed(() => props.sessionId ? `/prd/${props.sessionId}` : '#')

function handleLogout() {
  authStore.logout()
}
</script>

<style scoped>
.user-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 6px;
  transition: background 0.2s;
}
.user-trigger:hover {
  background: var(--sidebar-hover);
}
.user-name {
  font-size: 13px;
  color: var(--text);
}
.tool-btn:focus-visible,
.user-trigger:focus-visible,
.status-chip.clickable:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
  border-radius: var(--radius);
}
</style>