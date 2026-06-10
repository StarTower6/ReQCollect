<template>
  <AppLayout>
    <div class="users-page">
      <!-- Header -->
      <div class="page-header">
        <div class="page-header-left">
          <el-button text size="small" @click="goBack">← 返回</el-button>
          <h2>用户管理</h2>
        </div>
        <el-button type="primary" size="default" @click="showAdd = true">+ 新增</el-button>
      </div>

      <!-- Compact stat bar -->
      <div class="stat-bar">
        <span class="stat-item">
          👥 总 <strong>{{ stats.total }}</strong>
        </span>
        <span class="stat-divider"></span>
        <span class="stat-item">
          ✅ 活跃 <strong>{{ stats.active }}</strong>
        </span>
        <span class="stat-divider"></span>
        <span class="stat-item">
          🔒 管理员 <strong>{{ stats.admin }}</strong>
        </span>
        <span class="stat-divider"></span>
        <span class="stat-item">
          🏢 部门 <strong>{{ stats.departments }}</strong>
        </span>
      </div>

      <!-- Filter bar -->
      <div class="filter-bar">
        <el-input
          v-model="searchQuery"
          placeholder="搜索用户名、显示名、邮箱..."
          clearable
          :prefix-icon="SearchIcon"
          class="search-input"
          size="default"
        />
        <el-select v-model="roleFilter" placeholder="角色筛选" clearable class="filter-select" size="default">
          <el-option label="全部角色" value="" />
          <el-option :label="roleLabel('admin')" value="admin" />
          <el-option :label="roleLabel('analyst')" value="analyst" />
          <el-option :label="roleLabel('reviewer')" value="reviewer" />
          <el-option :label="roleLabel('business')" value="business" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable class="filter-select" size="default">
          <el-option label="全部状态" value="" />
          <el-option label="活跃" value="active" />
          <el-option label="已禁用" value="inactive" />
        </el-select>
      </div>

      <!-- Table -->
      <el-table
        ref="tableRef"
        :data="paginatedUsers"
        v-loading="loading"
        stripe
        style="width: 100%"
        empty-text="暂无用户数据"
        @selection-change="onSelectionChange"
        @row-click="onRowClick"
        :row-class-name="rowClassName"
        :header-cell-style="{ background: '#f5f7fa', color: '#303133' }"
      >
        <el-table-column type="selection" width="36" />
        <el-table-column label="用户" min-width="200">
          <template #default="{ row }">
            <div class="user-cell">
              <el-avatar :size="30" class="user-avatar" :class="{ 'avatar-inactive': !row.is_active }">
                {{ row.display_name?.[0] || row.username[0] }}
              </el-avatar>
              <div class="user-meta">
                <span class="user-name" :class="{ 'text-inactive': !row.is_active }">{{ row.display_name || row.username }}</span>
                <span class="user-account" :class="{ 'text-inactive': !row.is_active }">@{{ row.username }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="department" label="部门" width="120">
          <template #default="{ row }">
            <span :class="{ 'text-inactive': !row.is_active }">{{ row.department || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)" size="small" effect="plain" :class="{ 'tag-inactive': !row.is_active }">
              {{ roleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <span :class="row.is_active ? 'dot-active' : 'dot-inactive'"></span>
            <span :class="row.is_active ? 'status-active' : 'status-inactive'">
              {{ row.is_active ? '活跃' : '禁用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click.stop="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Bottom bar -->
      <div class="bottom-bar">
        <span class="selected-info" v-if="selectedUsers.length > 0">已选 {{ selectedUsers.length }} 项</span>
        <span class="selected-info" v-else></span>
        <el-pagination
          v-if="total > 0"
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          small
        />
      </div>

      <!-- Add dialog -->
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
              <el-form-item label="显示名">
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
          <el-form-item label="邮箱">
            <el-input v-model="addForm.email" placeholder="user@company.com" />
          </el-form-item>
          <el-form-item label="部门">
            <el-input v-model="addForm.department" placeholder="如：财务部、IT部" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showAdd = false">取消</el-button>
          <el-button type="primary" :loading="addLoading" @click="handleAdd">创建</el-button>
        </template>
      </el-dialog>

      <!-- Detail drawer -->
      <el-drawer
        v-model="showDetail"
        :title="detailUser ? (detailUser.display_name || detailUser.username) : ''"
        size="420px"
        :close-on-click-modal="false"
      >
        <template v-if="detailUser">
          <div class="drawer-header">
            <el-avatar :size="48" class="drawer-avatar">{{ detailUser.display_name?.[0] || detailUser.username[0] }}</el-avatar>
            <div class="drawer-header-meta">
              <span class="drawer-username">@{{ detailUser.username }}</span>
              <el-tag :type="roleTagType(detailUser.role)" size="small" effect="plain">{{ roleLabel(detailUser.role) }}</el-tag>
            </div>
          </div>

          <el-divider />

          <el-form :model="detailForm" label-width="70px" label-position="left" size="default">
            <el-form-item label="显示名">
              <el-input v-model="detailForm.display_name" />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="detailForm.email" />
            </el-form-item>
            <el-form-item label="部门">
              <el-input v-model="detailForm.department" />
            </el-form-item>
            <el-form-item label="角色">
              <el-select v-model="detailForm.role" style="width:100%">
                <el-option label="业务方" value="business" />
                <el-option label="分析师" value="analyst" />
                <el-option label="审核人" value="reviewer" />
                <el-option label="管理员" value="admin" />
              </el-select>
            </el-form-item>
            <el-form-item label="来源">
              <el-input :model-value="detailUser.source" disabled />
            </el-form-item>
            <el-form-item label="创建时间">
              <el-input :model-value="formatDateTime(detailUser.created_at)" disabled />
            </el-form-item>
            <el-form-item label="状态">
              <el-switch
                v-if="detailUser.username !== 'admin'"
                :model-value="detailUser.is_active"
                :loading="switching === detailUser.id"
                @change="(val: boolean) => toggleStatus(detailUser!, val)"
              />
              <span v-else class="disabled-tag">—</span>
            </el-form-item>
          </el-form>

          <el-divider />

          <div class="drawer-actions">
            <el-popconfirm
              v-if="detailUser.username !== 'admin'"
              title="确定删除此用户？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="handleDeleteFromDrawer"
            >
              <template #reference>
                <el-button type="danger" size="default" plain>删除用户</el-button>
              </template>
            </el-popconfirm>
            <el-button type="primary" size="default" :loading="savingDetail" @click="saveDetail">保存</el-button>
          </div>
        </template>
      </el-drawer>
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
  created_at?: string
  updated_at?: string
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
const statusFilter = ref('')

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
  if (statusFilter.value === 'active') {
    list = list.filter(u => u.is_active)
  } else if (statusFilter.value === 'inactive') {
    list = list.filter(u => !u.is_active)
  }
  return list
})

// Pagination
const page = ref(1)
const pageSize = ref(10)

watch([searchQuery, roleFilter, statusFilter], () => { page.value = 1 })

const total = computed(() => filteredUsers.value.length)
const paginatedUsers = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredUsers.value.slice(start, start + pageSize.value)
})

// Selection
const tableRef = ref()
const selectedUsers = ref<UserRow[]>([])

function onSelectionChange(rows: UserRow[]) {
  selectedUsers.value = rows
}

// Row click → open detail
function onRowClick(row: UserRow) {
  openDetail(row)
}

// Row class for inactive users
function rowClassName({ row }: { row: UserRow }) {
  if (!row.is_active) return 'row-inactive'
  return ''
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
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
}

// Detail drawer
const showDetail = ref(false)
const detailUser = ref<UserRow | null>(null)
const savingDetail = ref(false)
const detailForm = reactive({
  display_name: '', email: '', department: '', role: '',
})

function openDetail(row: UserRow) {
  detailUser.value = row
  detailForm.display_name = row.display_name
  detailForm.email = row.email
  detailForm.department = row.department
  detailForm.role = row.role
  showDetail.value = true
}

async function saveDetail() {
  if (!detailUser.value) return
  savingDetail.value = true
  try {
    await apiPatch(`/auth/users/${detailUser.value.id}`, { ...detailForm })
    ElMessage.success('用户信息已更新')
    showDetail.value = false
    await loadUsers()
  } catch (e: any) {
    ElMessage.error(e.message || '更新失败')
  } finally {
    savingDetail.value = false
  }
}

async function handleDeleteFromDrawer() {
  if (!detailUser.value) return
  try {
    await apiDelete(`/auth/users/${detailUser.value.id}`)
    ElMessage.success('用户已删除')
    showDetail.value = false
    page.value = 1
    await loadUsers()
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

// ── Helpers ──

function roleTagType(role: string): string {
  const map: Record<string, string> = { admin: 'danger', analyst: 'primary', reviewer: 'warning', business: 'success' }
  return map[role] || 'info'
}

function roleLabel(role: string): string {
  const map: Record<string, string> = { admin: '管理员', analyst: '分析师', reviewer: '审核人', business: '业务方' }
  return map[role] || role
}

function formatDateTime(d: string | undefined): string {
  if (!d) return '—'
  try { return new Date(d).toLocaleString('zh-CN') } catch { return '—' }
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

async function toggleStatus(row: UserRow, active: boolean) {
  switching.value = row.id
  try {
    await apiPatch(`/auth/users/${row.id}/status`, { is_active: active })
    row.is_active = active
    ElMessage.success(active ? '用户已启用' : '用户已禁用')
    // Refresh to update the drawer form
    await loadUsers()
    if (detailUser.value?.id === row.id) {
      detailUser.value = allUsers.value.find(u => u.id === row.id) || null
    }
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
  margin-bottom: 16px;
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

/* ── Compact stat bar ── */

.stat-bar {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 10px 16px;
  margin-bottom: 16px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #f0f0f5;
  font-size: 13px;
  color: #4e5969;
}

.stat-item {
  padding: 0 16px;
}

.stat-item:first-child {
  padding-left: 0;
}

.stat-item strong {
  color: #1d2129;
  font-size: 15px;
}

.stat-divider {
  width: 1px;
  height: 18px;
  background: #e5e6eb;
}

/* ── Filter ── */

.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.search-input {
  width: 260px;
}

.filter-select {
  width: 130px;
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

.user-avatar.avatar-inactive {
  background: #d9d9d9;
}

.user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.user-name {
  font-weight: 500;
  font-size: 14px;
}

.user-account {
  font-size: 12px;
  color: #86909c;
}

.text-inactive {
  color: #c0c4cc !important;
}

.tag-inactive {
  opacity: 0.5;
}

/* Status dots */
.dot-active {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #52c41a;
  margin-right: 4px;
  vertical-align: middle;
}

.dot-inactive {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d9d9d9;
  margin-right: 4px;
  vertical-align: middle;
}

.status-active {
  font-size: 13px;
  color: #52c41a;
  vertical-align: middle;
}

.status-inactive {
  font-size: 13px;
  color: #c0c4cc;
  vertical-align: middle;
}

/* ── Row class for inactive users ── */

:deep(.row-inactive) {
  color: #c0c4cc;
}

:deep(.row-inactive td) {
  color: #c0c4cc;
}

/* ── Bottom bar ── */

.bottom-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding: 4px 0;
}

.selected-info {
  font-size: 13px;
  color: #606266;
  min-width: 100px;
}

/* ── Drawer ── */

.drawer-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 0 8px;
}

.drawer-avatar {
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  font-weight: 600;
  flex-shrink: 0;
}

.drawer-header-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.drawer-username {
  font-size: 14px;
  font-weight: 500;
  color: #4e5969;
}

.drawer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.disabled-tag {
  color: #c0c4cc;
  font-size: 12px;
}

/* ── Responsive ── */

@media (max-width: 768px) {
  .stat-bar {
    flex-wrap: wrap;
    gap: 4px;
  }
  .stat-divider {
    display: none;
  }
  .filter-bar {
    flex-direction: column;
  }
  .search-input {
    width: 100%;
  }
}
</style>
