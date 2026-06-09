<template>
  <AppLayout>
    <div class="users-page">
      <!-- 返回 + 标题 -->
      <div class="page-header">
        <div class="page-header-left">
          <el-button text size="small" @click="goBack">← 返回</el-button>
          <h2>用户管理</h2>
        </div>
        <el-button type="primary" size="default" @click="showAdd = true">
          + 新增用户
        </el-button>
      </div>

      <!-- 统计卡片 -->
      <div class="stat-cards">
        <div class="stat-card-item">
          <span class="stat-icon users-icon">👥</span>
          <div class="stat-body">
            <span class="stat-num">{{ stats.total }}</span>
            <span class="stat-desc">总用户</span>
          </div>
        </div>
        <div class="stat-card-item">
          <span class="stat-icon active-icon">✅</span>
          <div class="stat-body">
            <span class="stat-num">{{ stats.active }}</span>
            <span class="stat-desc">活跃用户</span>
          </div>
        </div>
        <div class="stat-card-item">
          <span class="stat-icon admin-icon">🔒</span>
          <div class="stat-body">
            <span class="stat-num">{{ stats.admin }}</span>
            <span class="stat-desc">管理员</span>
          </div>
        </div>
        <div class="stat-card-item">
          <span class="stat-icon dept-icon">🏢</span>
          <div class="stat-body">
            <span class="stat-num">{{ stats.departments }}</span>
            <span class="stat-desc">覆盖部门</span>
          </div>
        </div>
      </div>

      <!-- 搜索 + 角色筛选 -->
      <div class="filter-bar">
        <el-input
          v-model="searchQuery"
          placeholder="搜索用户名、显示名、邮箱..."
          clearable
          :prefix-icon="SearchIcon"
          class="search-input"
          size="default"
        />
        <el-select v-model="roleFilter" placeholder="角色筛选" clearable class="role-select" size="default">
          <el-option label="全部角色" value="" />
          <el-option :label="roleLabel('admin')" value="admin" />
          <el-option :label="roleLabel('analyst')" value="analyst" />
          <el-option :label="roleLabel('reviewer')" value="reviewer" />
          <el-option :label="roleLabel('business')" value="business" />
        </el-select>
      </div>

      <!-- 表格 -->
      <el-table
        :data="paginatedUsers"
        v-loading="loading"
        stripe
        style="width: 100%"
        empty-text="暂无用户数据"
        :header-cell-style="{ background: '#f5f7fa', color: '#303133' }"
      >
        <el-table-column label="用户" width="220">
          <template #default="{ row }">
            <div class="user-cell">
              <el-avatar :size="36" class="user-avatar">{{ row.display_name?.[0] || row.username[0] }}</el-avatar>
              <div class="user-meta">
                <span class="user-name">{{ row.display_name || row.username }}</span>
                <span class="user-account">@{{ row.username }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" width="200">
          <template #default="{ row }">
            <span class="email-text">{{ row.email || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="department" label="部门" width="130">
          <template #default="{ row }">
            <span>{{ row.department || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)" size="small" effect="plain">
              {{ roleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="70" />
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-switch
              v-if="row.username !== 'admin'"
              :model-value="row.is_active"
              :loading="switching === row.id"
              size="small"
              @change="(val: boolean) => toggleStatus(row, val)"
            />
            <span v-else class="disabled-tag">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="startEdit(row)">编辑</el-button>
            <el-popconfirm
              v-if="row.username !== 'admin'"
              title="确定删除此用户？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button size="small" text type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrap" v-if="total > 0">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          small
        />
      </div>

      <!-- 新增用户对话框 -->
      <el-dialog v-model="showAdd" title="新增用户" width="480px" :close-on-click-modal="false">
        <el-form
          ref="addFormRef"
          :model="addForm"
          :rules="addRules"
          label-width="70px"
          label-position="left"
          size="default"
        >
          <el-form-item label="用户名" prop="username">
            <el-input v-model="addForm.username" placeholder="登录用的账号" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="addForm.password" type="password" show-password placeholder="至少 6 位" />
          </el-form-item>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="显示名" prop="display_name">
                <el-input v-model="addForm.display_name" placeholder="用户友好的名称" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="角色" prop="role">
                <el-select v-model="addForm.role" style="width:100%">
                  <el-option label="业务方" value="business" />
                  <el-option label="分析师" value="analyst" />
                  <el-option label="审核人" value="reviewer" />
                  <el-option label="管理员" value="admin" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="addForm.email" placeholder="user@company.com" />
          </el-form-item>
          <el-form-item label="部门" prop="department">
            <el-input v-model="addForm.department" placeholder="如：财务部、IT部" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showAdd = false">取消</el-button>
          <el-button type="primary" :loading="addLoading" @click="handleAdd">创建</el-button>
        </template>
      </el-dialog>

      <!-- 编辑用户对话框 -->
      <el-dialog v-model="showEdit" title="编辑用户" width="480px" :close-on-click-modal="false">
        <el-form
          ref="editFormRef"
          :model="editForm"
          label-width="70px"
          label-position="left"
          size="default"
        >
          <el-form-item label="用户名">
            <el-input :model-value="editForm.username" disabled />
          </el-form-item>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="显示名">
                <el-input v-model="editForm.display_name" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="角色">
                <el-select v-model="editForm.role" style="width:100%">
                  <el-option label="业务方" value="business" />
                  <el-option label="分析师" value="analyst" />
                  <el-option label="审核人" value="reviewer" />
                  <el-option label="管理员" value="admin" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="邮箱">
            <el-input v-model="editForm.email" />
          </el-form-item>
          <el-form-item label="部门">
            <el-input v-model="editForm.department" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showEdit = false">取消</el-button>
          <el-button type="primary" :loading="editLoading" @click="handleEdit">保存</el-button>
        </template>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search as SearchIcon } from '@element-plus/icons-vue'
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

const allUsers = ref<UserRow[]>([])
const loading = ref(false)
const switching = ref('')
const router = useRouter()

function goBack() {
  router.push('/chat')
}

// Stats
const stats = computed(() => {
  const users = allUsers.value
  return {
    total: users.length,
    active: users.filter(u => u.is_active).length,
    admin: users.filter(u => u.role === 'admin').length,
    departments: new Set(users.map(u => u.department).filter(Boolean)).size,
  }
})

// Filter
const searchQuery = ref('')
const roleFilter = ref('')

const filteredUsers = computed(() => {
  let list = allUsers.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(u =>
      u.username.toLowerCase().includes(q) ||
      (u.display_name || '').toLowerCase().includes(q) ||
      (u.email || '').toLowerCase().includes(q)
    )
  }
  if (roleFilter.value) {
    list = list.filter(u => u.role === roleFilter.value)
  }
  return list
})

// Pagination
const page = ref(1)
const pageSize = ref(10)

// Reset to page 1 when filter changes
watch([searchQuery, roleFilter], () => { page.value = 1 })

const total = computed(() => filteredUsers.value.length)
const paginatedUsers = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredUsers.value.slice(start, start + pageSize.value)
})

// Add dialog
const showAdd = ref(false)
const addLoading = ref(false)
const addFormRef = ref()
const addForm = reactive({
  username: '', password: '', display_name: '', email: '', department: '', role: 'business',
})
const addRules: Record<string, any> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
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
    allUsers.value = res.users
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
    page.value = 1
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
    page.value = 1
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

/* ── Header ── */

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-header-left {
  display: flex;
  align-items: center;
  gap: 4px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

/* ── Stat Cards ── */

.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  border: 1px solid #ebeef5;
}

.stat-icon {
  font-size: 28px;
  line-height: 1;
}

.stat-body {
  display: flex;
  flex-direction: column;
}

.stat-num {
  font-size: 26px;
  font-weight: 700;
  color: #1d2129;
  line-height: 1.2;
}

.stat-desc {
  font-size: 13px;
  color: #86909c;
  margin-top: 2px;
}

/* ── Filter ── */

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-input {
  width: 280px;
}

.role-select {
  width: 140px;
}

/* ── Table ── */

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  font-weight: 600;
  flex-shrink: 0;
}

.user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.user-name {
  font-weight: 500;
  color: #1d2129;
  font-size: 14px;
}

.user-account {
  font-size: 12px;
  color: #86909c;
}

.email-text {
  color: #4e5969;
  font-size: 13px;
}

.disabled-tag {
  color: #c0c4cc;
  font-size: 12px;
}

/* ── Pagination ── */

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding: 8px 0;
}

/* ── Responsive ── */

@media (max-width: 768px) {
  .stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  .filter-bar {
    flex-direction: column;
  }
  .search-input {
    width: 100%;
  }
}
</style>
