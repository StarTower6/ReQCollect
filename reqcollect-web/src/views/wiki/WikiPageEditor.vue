<template>
  <AppLayout>
    <div class="wiki-editor-page">
      <!-- Top bar -->
      <div class="editor-topbar">
        <el-button text size="small" @click="handleCancel">← 返回</el-button>
        <div class="editor-topbar-right">
          <span class="editor-mode">{{ isNew ? '新建页面' : '编辑页面' }}</span>
          <el-button size="small" :loading="aiLoading" @click="handleAISuggest" v-if="!isNew">
            🤖 AI 建议补充
          </el-button>
          <el-button type="primary" size="small" :loading="saving" @click="handleSave">
            {{ isNew ? '创建' : '保存' }}
          </el-button>
        </div>
      </div>

      <!-- AI suggestion panel -->
      <div v-if="aiSuggestion" class="ai-suggestion-panel">
        <div class="ai-suggestion-header">
          <span>🤖 AI 建议补充以下内容</span>
          <div class="ai-suggestion-actions">
            <el-button size="small" @click="applySuggestion">采纳</el-button>
            <el-button size="small" text @click="aiSuggestion = ''">关闭</el-button>
          </div>
        </div>
        <div class="ai-suggestion-body markdown-body" v-html="aiSuggestionHtml" />
      </div>

      <!-- Editor body -->
      <div class="editor-body" v-if="loaded">
        <div class="editor-left">
          <el-input
            v-model="form.title"
            placeholder="页面标题"
            class="title-input"
            size="large"
          />
          <textarea
            v-model="form.content"
            class="editor-textarea"
            placeholder="在此编写 Markdown 内容..."
          />
        </div>
        <div class="editor-divider"></div>
        <div class="editor-right">
          <div class="preview-header">预览</div>
          <div class="preview-body markdown-body" v-html="renderedContent" />
        </div>
      </div>

      <div v-else v-loading="true" style="height:300px" />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { fetchWikiPage, createWikiPage, updateWikiPage, aiSuggestContent } from '@/api/wiki'
import AppLayout from '@/components/layout/AppLayout.vue'

const route = useRoute()
const router = useRouter()

const isNew = computed(() => !route.params.pageId || route.params.pageId === 'new')
const workspaceId = computed(() => route.params.id as string)
const pageId = computed(() => route.params.pageId as string)

const loaded = ref(false)
const saving = ref(false)
const aiLoading = ref(false)
const aiSuggestion = ref('')
const form = reactive({ title: '', content: '' })

const renderedContent = computed(() => {
  try {
    return marked(form.content || '')
  } catch {
    return form.content || ''
  }
})

const aiSuggestionHtml = computed(() => {
  try {
    return marked(aiSuggestion.value || '')
  } catch {
    return aiSuggestion.value || ''
  }
})

function handleCancel() {
  if (isNew.value) {
    router.push(`/workspaces/${workspaceId.value}`)
  } else {
    router.push(`/workspaces/${workspaceId.value}/wiki/${pageId.value}`)
  }
}

async function handleSave() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  saving.value = true
  try {
    if (isNew.value) {
      const page = await createWikiPage({
        workspace_id: workspaceId.value,
        title: form.title.trim(),
        content: form.content,
      })
      ElMessage.success('创建成功')
      router.push(`/workspaces/${workspaceId.value}/wiki/${page.id}`)
    } else {
      await updateWikiPage(pageId.value, {
        title: form.title.trim(),
        content: form.content,
      })
      ElMessage.success('已保存')
      router.push(`/workspaces/${workspaceId.value}/wiki/${pageId.value}`)
    }
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleAISuggest() {
  if (!form.content.trim() && !form.title.trim()) {
    ElMessage.warning('请先写一些内容，AI 才能分析缺失章节')
    return
  }
  aiLoading.value = true
  try {
    const suggestion = await aiSuggestContent({
      page_id: pageId.value,
      title: form.title,
      existing_content: form.content,
    })
    aiSuggestion.value = suggestion
  } catch (e: any) {
    ElMessage.error(e.message || 'AI 建议失败')
  } finally {
    aiLoading.value = false
  }
}

function applySuggestion() {
  form.content += '\n\n' + aiSuggestion.value
  aiSuggestion.value = ''
  ElMessage.success('已采纳 AI 建议')
}

onMounted(async () => {
  if (!isNew.value) {
    try {
      const page = await fetchWikiPage(pageId.value)
      form.title = page.title
      form.content = page.content
    } catch {
      ElMessage.error('加载页面失败')
    }
  }
  loaded.value = true
})
</script>

<style scoped>
.wiki-editor-page {
  height: calc(100vh - var(--topbar-height, 0px));
  display: flex;
  flex-direction: column;
}

.editor-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  border-bottom: 1px solid var(--line);
  flex-shrink: 0;
}

.editor-topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.editor-mode {
  font-size: 13px;
  color: var(--muted);
}

.editor-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.editor-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px 20px;
  overflow-y: auto;
}

.editor-divider {
  width: 1px;
  background: var(--line);
  flex-shrink: 0;
}

.editor-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px 20px;
  overflow-y: auto;
  background: var(--sidebar);
}

.title-input {
  margin-bottom: 12px;
}

.title-input :deep(.el-input__inner) {
  font-size: 20px;
  font-weight: 600;
}

.editor-textarea {
  flex: 1;
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  font-size: 14px;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  line-height: 1.6;
  resize: none;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.editor-textarea:focus {
  border-color: var(--brand);
}

.preview-header {
  font-size: 13px;
  font-weight: 500;
  color: var(--muted);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.preview-body {
  line-height: 1.8;
  font-size: 15px;
}

/* Table styling for editor preview */
.preview-body :deep(table),
.ai-suggestion-body :deep(table) {
  display: table;
  width: 100%;
  border-collapse: collapse;
  border-spacing: 0;
  overflow: auto;
  margin: 12px 0;
}
.preview-body :deep(table th),
.ai-suggestion-body :deep(table th) {
  font-weight: 600;
  background: var(--sidebar);
  border: 1px solid var(--line);
  padding: 8px 12px;
  text-align: left;
}
.preview-body :deep(table td),
.ai-suggestion-body :deep(table td) {
  border: 1px solid var(--line);
  padding: 8px 12px;
}
.preview-body :deep(table tr:nth-child(2n)),
.ai-suggestion-body :deep(table tr:nth-child(2n)) {
  background: var(--sidebar);
}

/* AI suggestion panel */
.ai-suggestion-panel {
  border: 1px solid var(--brand-soft);
  background: var(--brand-soft);
  border-radius: 8px;
  margin: 8px 24px;
  padding: 12px 16px;
  flex-shrink: 0;
}

.ai-suggestion-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
}

.ai-suggestion-actions {
  display: flex;
  gap: 8px;
}

.ai-suggestion-body {
  font-size: 14px;
  line-height: 1.6;
  max-height: 300px;
  overflow-y: auto;
  padding: 8px 12px;
  background: var(--panel);
  border-radius: 6px;
}

@media (max-width: 768px) {
  .editor-body {
    flex-direction: column;
  }
  .editor-divider {
    display: none;
  }
}
</style>
