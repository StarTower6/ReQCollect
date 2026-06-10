<template>
  <AppLayout>
    <div class="wiki-editor-page">
      <!-- Top bar -->
      <div class="editor-topbar">
        <el-button text size="small" @click="handleCancel">← 返回</el-button>
        <div class="editor-topbar-right">
          <span class="editor-mode">{{ isNew ? '新建页面' : '编辑页面' }}</span>
          <el-button type="primary" size="small" :loading="saving" @click="handleSave">
            {{ isNew ? '创建' : '保存' }}
          </el-button>
        </div>
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
import { fetchWikiPage, createWikiPage, updateWikiPage } from '@/api/wiki'
import AppLayout from '@/components/layout/AppLayout.vue'

const route = useRoute()
const router = useRouter()

const isNew = computed(() => !route.params.pageId || route.params.pageId === 'new')
const workspaceId = computed(() => route.params.id as string)
const pageId = computed(() => route.params.pageId as string)

const loaded = ref(false)
const saving = ref(false)
const form = reactive({ title: '', content: '' })

const renderedContent = computed(() => {
  try {
    return marked(form.content || '')
  } catch {
    return form.content || ''
  }
})

function handleCancel() {
  if (isNew.value) {
    router.push(`/workspace/${workspaceId.value}`)
  } else {
    router.push(`/workspace/${workspaceId.value}/wiki/${pageId.value}`)
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
      router.push(`/workspace/${workspaceId.value}/wiki/${page.id}`)
    } else {
      await updateWikiPage(pageId.value, {
        title: form.title.trim(),
        content: form.content,
      })
      ElMessage.success('已保存')
      router.push(`/workspace/${workspaceId.value}/wiki/${pageId.value}`)
    }
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
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
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.editor-topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.editor-mode {
  font-size: 13px;
  color: #86909c;
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
  background: #ebeef5;
  flex-shrink: 0;
}

.editor-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px 20px;
  overflow-y: auto;
  background: #fafafa;
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
  border: 1px solid #dcdfe6;
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
  border-color: #409eff;
}

.preview-header {
  font-size: 13px;
  font-weight: 500;
  color: #86909c;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.preview-body {
  line-height: 1.8;
  font-size: 15px;
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
