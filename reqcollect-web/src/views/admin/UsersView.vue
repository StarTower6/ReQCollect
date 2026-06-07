<template>
  <div class="users-page">
    <div class="page-header">
      <h2>用户管理</h2>
      <el-tag type="warning">管理员</el-tag>
    </div>

    <el-table :data="users" v-loading="loading" stripe style="width: 100%">
      <el-table-column prop="username" label="用户名" width="120" />
      <el-table-column prop="display_name" label="显示名" width="150" />
      <el-table-column prop="email" label="邮箱" width="200" />
      <el-table-column prop="department" label="部门" width="150" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="roleTagType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="source" label="来源" width="80" />
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
            {{ row.is_active ? '正常' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-switch
            v-if="row.username !== 'admin'"
            :model-value="row.is_active"
            :loading="switching === row.id"
            @change="(val: boolean) => toggleStatus(row, val)"
          />
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiGet, apiPatch } from '@/api/client'

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

const users = ref<UserRow[]>([])
const loading = ref(false)
const switching = ref('')

function roleTagType(role: string): string {
  const map: Record<string, string> = { admin: 'danger', analyst: 'primary', reviewer: 'warning', business: 'info' }
  return map[role] || 'info'
}

function roleLabel(role: string): string {
  const map: Record<string, string> = { admin: '管理员', analyst: '分析师', reviewer: '审核人', business: '业务方' }
  return map[role] || role
}

async function loadUsers() {
  loading.value = true
  try {
    const res: any = await apiGet('/auth/users')
    users.value = res.users
  } catch (e: any) {
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
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
  gap: 12px;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
}
</style>
