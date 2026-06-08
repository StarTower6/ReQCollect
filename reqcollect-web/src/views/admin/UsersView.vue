<template>
  <AppLayout>
    <div class="users-page">
      <div class="page-header">
        <div class="page-header-left">
          <el-button text size="small" @click="goBack">← 返回</el-button>
          <h2>用户管理</h2>
        </div>
        <el-button type="primary" size="small" @click="showAdd = true">
          + 新增用户
        </el-button>
      </div>

      <el-table
        :data="users"
        v-loading="loading"
        stripe
        style="width: 100%"
        empty-text="暂无用户数据"
      >
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="display_name" label="显示名" width="150" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column prop="department" label="部门" width="140" />
        <el-table-column prop="role" label="角色" width="90">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="70" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-switch
              v-if="row.username !== 'admin'"
              :model-value="row.is_active"
              :loading="switching === row.id"
              @change="(val: boolean) => toggleStatus(row, val)"
            />
            <span v-else style="color:#999;font-size:12px">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="startEdit(row)">编辑</el-button>
            <el-popconfirm
              v-if="row.username !== 'admin'"
              title="确定删除此用户？"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 新增用户对话框 -->
      <el-dialog v-model="showAdd" title="新增用户" width="450px">
        <el-form
          ref="addFormRef"
          :model="addForm"
          :rules="addRules"
          label-width="80px"
          label-position="left"
        >
          <el-form-item label="用户名" prop="username">
            <el-input v-model="addForm.username" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="addForm.password" type="password" show-password />
          </el-form-item>
          <el-form-item label="显示名" prop="display_name">
            <el-input v-model="addForm.display_name" />
          </el-form-item>
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="addForm.email" />
          </el-form-item>
          <el-form-item label="部门" prop="department">
            <el-input v-model="addForm.department" />
          </el-form-item>
          <el-form-item label="角色" prop="role">
            <el-select v-model="addForm.role" style="width:100%">
              <el-option label="业务方" value="business" />
              <el-option label="分析师" value="analyst" />
              <el-option label="审核人" value="reviewer" />
              <el-option label="管理员" value="admin" />
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showAdd = false">取消</el-button>
          <el-button type="primary" :loading="addLoading" @click="handleAdd">
            创建
          </el-button>
        </template>
      </el-dialog>

      <!-- 编辑用户对话框 -->
      <el-dialog v-model="showEdit" title="编辑用户" width="450px">
        <el-form
          ref="editFormRef"
          :model="editForm"
          label-width="80px"
          label-position="left"
        >
          <el-form-item label="用户名">
            <el-input :model-value="editForm.username" disabled />
          </el-form-item>
          <el-form-item label="显示名">
            <el-input v-model="editForm.display_name" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="editForm.email" />
          </el-form-item>
          <el-form-item label="部门">
            <el-input v-model="editForm.department" />
          </el-form-item>
          <el-form-item label="角色">
            <el-select v-model="editForm.role" style="width:100%">
              <el-option label="业务方" value="business" />
              <el-option label="分析师" value="analyst" />
              <el-option label="审核人" value="reviewer" />
              <el-option label="管理员" value="admin" />
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showEdit = false">取消</el-button>
          <el-button type="primary" :loading="editLoading" @click="handleEdit">
            保存
          </el-button>
        </template>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apiGet, apiPost, apiPatch, apiDelete } from '@/api/client'
import AppLayout from '@/components/layout/AppLayout.vue'

// ── Types ──

interface UserRow {
  id: string
  username: string
  display_name: string
  email: string
  department: string
  role: string
  source: string
  is_active: boolean
}

// ── State ──

const users = ref<UserRow[]>([])
const loading = ref(false)
const switching = ref('')
const router = useRouter()

function goBack() {
  router.push('/chat')
}

// Add dialog
const showAdd = ref(false)
const addLoading = ref(false)
const addFormRef = ref()
const addForm = reactive({
  username: '', password: '', display_name: '', email: '', department: '', role: 'business',
})
const addRules: Record<string, any> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

// Edit dialog
const showEdit = ref(false)
const editLoading = ref(false)
const editFormRef = ref()
const editForm = reactive({
  id: '', username: '', display_name: '', email: '', department: '', role: '',
})

// ── Helpers ──

function roleTagType(role: string): string {
  const map: Record<string, string> = { admin: 'danger', analyst: 'primary', reviewer: 'warning', business: 'info' }
  return map[role] || 'info'
}

function roleLabel(role: string): string {
  const map: Record<string, string> = { admin: '管理员', analyst: '分析师', reviewer: '审核人', business: '业务方' }
  return map[role] || role
}

// ── CRUD ──

async function loadUsers() {
  loading.value = true
  try {
    const res: any = await apiGet('/auth/users')
    users.value = res.users
  } catch {
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

async function handleAdd() {
  const valid = await addFormRef.value?.validate().catch(() => false)
  if (!valid) return
  addLoading.value = true
  try {
    await apiPost('/auth/register', { ...addForm })
    ElMessage.success('用户创建成功')
    showAdd.value = false
    addForm.username = ''; addForm.password = ''; addForm.display_name = ''
    addForm.email = ''; addForm.department = ''; addForm.role = 'business'
    await loadUsers()
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    addLoading.value = false
  }
}

function startEdit(row: UserRow) {
  editForm.id = row.id
  editForm.username = row.username
  editForm.display_name = row.display_name
  editForm.email = row.email
  editForm.department = row.department
  editForm.role = row.role
  showEdit.value = true
}

async function handleEdit() {
  editLoading.value = true
  try {
    await apiPatch(`/auth/users/${editForm.id}`, {
      display_name: editForm.display_name,
      email: editForm.email,
      department: editForm.department,
      role: editForm.role,
    })
    ElMessage.success('用户信息已更新')
    showEdit.value = false
    await loadUsers()
  } catch (e: any) {
    ElMessage.error(e.message || '更新失败')
  } finally {
    editLoading.value = false
  }
}

async function handleDelete(row: UserRow) {
  try {
    await apiDelete(`/auth/users/${row.id}`)
    ElMessage.success('用户已删除')
    await loadUsers()
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

async function toggleStatus(row: UserRow, active: boolean) {
  switching.value = row.id
  try {
    await apiPatch(`/auth/users/${row.id}/status`, { is_active: active })
    row.is_active = active
    ElMessage.success(active ? '用户已启用' : '用户已禁用')
  } catch {
    ElMessage.error('操作失败')
  } finally {
    switching.value = ''
  }
}

onMounted(loadUsers)
</script>

<style scoped>
.users-page {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-header-left {
  display: flex;
  align-items: center;
  gap: 4px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
}
</style>
