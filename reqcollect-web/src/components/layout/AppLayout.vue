<template>
  <div class="app-layout">
    <SideBar @import-doc="showImport = true" />
    <ImportDialog v-model:visible="showImport" />
    <div class="main-area">
      <div class="main">
        <TopBar
          :title="title"
          :session-id="sessionStore.currentId"
          :sufficiency-percent="sufficiencyPercent"
          @show-profile="drawerVisible = true"
        />
        <slot />
      </div>
    </div>
    <!-- File tree sidebar (replaces old ProfilePanel) -->
    <FileTreePanel
      v-if="showFileTree"
      :workspace-id="currentFileWsId"
      :referenced-files="referencedFiles"
      @reference="handleFileReference"
      @remove-reference="handleRemoveReference"
    />
    <!-- Profile drawer (clicked from TopBar sufficiency button) -->
    <el-drawer v-model="drawerVisible" title="需求画像" size="360px" append-to-body>
      <ProfilePanel v-if="sessionStore.currentId" :profile="profileStore.profile" :percent="sufficiencyPercent" />
      <div v-else style="color:var(--muted-light);padding:20px;text-align:center;font-size:13px">选择会话查看需求画像</div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, provide } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useProfileStore } from '@/stores/profile'
import SideBar from './SideBar.vue'
import TopBar from './TopBar.vue'
import ProfilePanel from '@/components/profile/ProfilePanel.vue'
import ImportDialog from '@/components/chat/ImportDialog.vue'
import FileTreePanel from '@/components/workspace/FileTreePanel.vue'

const sessionStore = useSessionStore()
const profileStore = useProfileStore()

const showFileTree = computed((): boolean => {
  return !!currentFileWsId.value
})

const currentFileWsId = computed((): string | null => {
  // Priority 1: In a chat session with associated workspace
  if (sessionStore.currentId && sessionStore.currentWorkspaceId) {
    return sessionStore.currentWorkspaceId as string
  }
  // Priority 2: Workspace expanded in sidebar
  if (sessionStore.expandedWsId && sessionStore.expandedWsId !== '__ungrouped__') {
    return sessionStore.expandedWsId as string
  }
  return null
})

const drawerVisible = ref(false)
const showImport = ref(false)
const referencedFiles = ref<string[]>([])

provide('referencedFiles', referencedFiles)

function handleFileReference(fp: string) {
  if (!referencedFiles.value.includes(fp))
    referencedFiles.value.push(fp)
}
function handleRemoveReference(fp: string) {
  referencedFiles.value = referencedFiles.value.filter(f => f !== fp)
}

const title = computed(() => {
  if (profileStore.profile.project_name) return profileStore.profile.project_name
  if (sessionStore.currentId) return '对话进行中'
  return 'ReQCollect'
})

const sufficiencyPercent = computed(() =>
  Math.round((profileStore.profile.sufficiency_score || 0) * 100)
)
</script>

<style scoped>
.app-layout { display: flex; height: 100vh; overflow: hidden; }
.main-area { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
</style>
