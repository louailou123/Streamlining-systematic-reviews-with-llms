import type { Pinia } from 'pinia';
import { createRouter, createWebHistory } from 'vue-router';

import { useAuthStore } from '@/stores/auth';

export function createAppRouter(pinia: Pinia) {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: '/login',
        name: 'login',
        component: () => import('@/pages/LoginPage.vue'),
        meta: { public: true, guestOnly: true },
      },
      {
        path: '/register',
        name: 'register',
        component: () => import('@/pages/RegisterPage.vue'),
        meta: { public: true, guestOnly: true },
      },
      {
        path: '/auth/callback',
        name: 'oauth-callback',
        component: () => import('@/pages/OAuthCallbackPage.vue'),
        meta: { public: true },
      },
      {
        path: '/',
        name: 'dashboard',
        component: () => import('@/pages/DashboardPage.vue'),
      },
      {
        path: '/research/:id',
        name: 'research-workspace',
        component: () => import('@/pages/ResearchWorkspacePage.vue'),
        props: true,
      },
      {
        path: '/:pathMatch(.*)*',
        redirect: '/',
      },
    ],
  });

  router.beforeEach(async (to) => {
    const authStore = useAuthStore(pinia);

    if (!authStore.initialized) {
      await authStore.initialize();
    }

    if (to.meta.guestOnly && authStore.isAuthenticated) {
      return { path: '/' };
    }

    if (!to.meta.public && !authStore.isAuthenticated) {
      return { path: '/login', query: { redirect: to.fullPath } };
    }

    return true;
  });

  return router;
}
