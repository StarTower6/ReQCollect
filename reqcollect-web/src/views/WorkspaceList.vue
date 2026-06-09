<template>
  <AppLayout>
    <div class="ws-list-page">
      <div class="page-header">
        <h2>工作空间</h2>
        <el-button type="primary" size="default" @click="showCreate = true">+ 新建项目</el-button>
      </div>

      <div v-if="loading" v-loading="loading" style="height:200px" />

      <div v-else-if="workspaces.length === 0" class="empty-state">
        <div class="empty-icon">📂</div>
        <p class="empty-title">暂无工作空间</p>
        <p class="empty-desc">创建第一个工作空间来管理您的项目需求</p>
      </div>

      <div v-else class="ws-grid">
        <div
          v-for="ws in workspaces"
          :key="ws.id"
          class="ws-card"
          @click="goWorkspace(ws.id)"
        >
          <div class="ws-card-header">
            <span class="ws-name">{{ ws.name }}</span>
            <el-tag v-if="ws.code" size="small" type="info">{{ ws.code }}</el-tag>
          </div>
          <p class="ws-desc">{{ ws.description || '暂无描述' }}</p>
          <div class="ws-meta">
            <span class="ws-time">{{ formatDate(ws.updated_at) }}</span>
          </div>
        </div>
      </div>

      <!-- Create dialog -->
      <el-dialog v-model="showCreate" title="新建项目" width="480px">
        <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
          <el-form-item label="项目名称" prop="name">
            <el-input v-model="form.name" placeholder="如：MES 系统升级" />
          </el-form-item>
          <el-form-item label="项目编码">
            <el-input v-model="form.code" placeholder="如：MES-2026（选填）" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="form.description" type="textarea" :rows="3" placeholder="项目简要描述（选填）" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showCreate = false">取消</el-button>
          <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
        </template>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchWorkspaces, createWorkspace } from '@/api/workspace'
import AppLayout from '@/components/layout/AppLayout.vue'

const router = useRouter()
const workspaces = ref<any[]>([])
const loading = ref(true)
const showCreate = ref(false)
const creating = ref(false)
const formRef = ref()
const form = reactive({ name: '', code: '', description: '' })
const rules = { name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }] }

function formatDate(d: string) {
  if (!d) return ''
  try { return new Date(d).toLocaleDateString('zh-CN') } catch { return '' }
}

function goWorkspace(id: string) {
  router.push(`/workspace/${id}`)
}

async function load() {
  loading.value = true
  try {
    workspaces.value = await fetchWorkspaces()
  } catch { ElMessage.error('加载失败') }
  finally { loading.value = false }
}

async function handleCreate() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  creating.value = true
  try {
    await createWorkspace({ ...form })
    ElMessage.success('工作空间创建成功')
    showCreate.value = false
    form.name = ''; form.code = ''; form.description = ''
    await load()
  } catch (e: any) { ElMessage.error(e.message || '创建失败') }
  finally { creating.value = false }
}

onMounted(load)
</script>

<style scoped>
.ws-list-page { padding: 24px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.page-header h2 { margin: 0; font-size: 20px; font-weight: 600; }

.empty-state { text-align: center; padding: 80px 0; color: #86909c; }
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-title { font-size: 16px; font-weight: 500; margin: 0 0 8px; color: #4e5969; }
.empty-desc { font-size: 14px; margin: 0; }

.ws-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.ws-card {
  padding: 20px; border-radius: 10px; background: #fff;
  border: 1px solid #ebeef5; cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.ws-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-color: #409eff; }
.ws-card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.ws-name { font-size: 16px; font-weight: 600; color: #1d2129; }
.ws-desc { font-size: 13px; color: #86909c; margin: 0 0 12px; line-height: 1.5; }
.ws-meta { font-size: 12px; color: #c0c4cc; }
</style>
