import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
    },
    {
      path: '/',
      redirect: '/workspaces',
    },
    {
      path: '/workspaces',
      name: 'WorkspaceList',
      component: () => import('@/views/WorkspaceList.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/workspace/:id',
      name: 'WorkspaceDetail',
      component: () => import('@/views/WorkspaceDetail.vue'),
      meta: { requiresAuth: true },
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
      path: '/prd/:sessionId',
      name: 'PrdView',
      component: () => import('@/views/PrdView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/users',
      name: 'AdminUsers',
      component: () => import('@/views/admin/UsersView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
  ],
})

// ── Navigation guard ──
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('reqcollect_token')
  const isAuthenticated = !!token

  if (to.path === '/login' && isAuthenticated) {
    next('/workspaces')
    return
  }

  if (to.meta.requiresAuth && !isAuthenticated) {
    next('/login')
    return
  }

  next()
})

export default router
