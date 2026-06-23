import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
  }
}

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/chat',
      name: 'Chat',
      component: () => import('@/views/ChatView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/chat/:sessionId',
      name: 'ChatWithSession',
      component: () => import('@/views/ChatView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/prd/:id',
      name: 'Prd',
      component: () => import('@/views/PrdView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/workspaces',
      name: 'WorkspaceList',
      component: () => import('@/views/WorkspaceList.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/workspaces/:id',
      name: 'WorkspaceDetail',
      component: () => import('@/views/WorkspaceDetail.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/workspaces/:id/wiki/:pageId',
      name: 'WikiPageView',
      component: () => import('@/views/wiki/WikiPageView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/workspaces/:id/wiki/:pageId/edit',
      name: 'WikiPageEditor',
      component: () => import('@/views/wiki/WikiPageEditor.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/workspaces/:id/proposals',
      name: 'ProposalList',
      component: () => import('@/views/proposal/ProposalListView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/workspaces/:id/proposals/:pid',
      name: 'ProposalDetail',
      component: () => import('@/views/proposal/ProposalDetailView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/workspaces/:id/proposals/kanban',
      name: 'ProposalKanban',
      component: () => import('@/views/proposal/ProposalKanbanView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/wiki/:id',
      name: 'WikiGraph',
      component: () => import('@/views/wiki/GraphView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/users',
      name: 'Users',
      component: () => import('@/views/admin/UsersView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/chat',
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth !== false && !authStore.token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && authStore.token) {
    next({ name: 'Chat' })
  } else {
    next()
  }
})

export default router
