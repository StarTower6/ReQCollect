<template>
  <div class="app-layout">
    <SideBar @new-chat="handleNewChat" />
    <div class="main-area">
      <div class="main">
        <TopBar
          :title="title"
          :session-id="sessionStore.currentId"
          :sufficiency-percent="sufficiencyPercent"
        />
        <slot />
      </div>
      <!-- Profile Panel for desktop -->
      <div class="profile-panel profile-panel-desktop" v-if="sessionStore.currentId && profileStore.profile.project_name !== undefined && windowWidth > 1200"
           style="width:300px;overflow-y:auto;border-left:1px solid var(--line);background:var(--panel);padding:16px">
        <ProfilePanel :profile="profileStore.profile" :percent="sufficiencyPercent" />
      </div>
    </div>
    <!-- Drawer for mobile -->
    <el-drawer v-model="drawerVisible" title="需求画像" size="320px" append-to-body>
      <ProfilePanel v-if="sessionStore.currentId" :profile="profileStore.profile" :percent="sufficiencyPercent" />
      <div v-else style="color:var(--muted-light);padding:20px;text-align:center;font-size:13px">选择会话查看需求画像</div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useProfileStore } from '@/stores/profile'
import SideBar from './SideBar.vue'
import TopBar from './TopBar.vue'
import ProfilePanel from '@/components/profile/ProfilePanel.vue'

const sessionStore = useSessionStore()
const profileStore = useProfileStore()
const router = useRouter()

const drawerVisible = ref(false)
const windowWidth = ref(window.innerWidth)

function onResize() { windowWidth.value = window.innerWidth }
onMounted(() => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))

const title = computed(() => {
  if (profileStore.profile.project_name) return profileStore.profile.project_name
  if (sessionStore.currentId) return '对话进行中'
  return 'ReQCollect'
})

const sufficiencyPercent = computed(() => Math.round((profileStore.profile.sufficiency_score || 0) * 100))

function handleNewChat() {
  const id = sessionStore.newSession()
  profileStore.clear()
  router.push(`/chat/${id}`)
}
</script>
