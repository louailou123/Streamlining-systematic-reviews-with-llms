import { computed, ref } from 'vue';
import { defineStore } from 'pinia';

import { authApi } from '@/api/auth';
import type { User } from '@/types/auth';

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null);
  const isLoading = ref(false);
  const initialized = ref(false);

  const isAuthenticated = computed(() => Boolean(window.localStorage.getItem('access_token')));

  function setTokens(accessToken: string, refreshToken: string) {
    window.localStorage.setItem('access_token', accessToken);
    window.localStorage.setItem('refresh_token', refreshToken);
  }

  async function loadUser() {
    if (!window.localStorage.getItem('access_token')) {
      user.value = null;
      return;
    }

    isLoading.value = true;
    try {
      user.value = await authApi.getProfile();
    } catch (error) {
      user.value = null;
      window.localStorage.removeItem('access_token');
      window.localStorage.removeItem('refresh_token');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function initialize() {
    if (initialized.value) {
      return;
    }

    try {
      await loadUser();
    } catch {
      // invalid session gets cleared in loadUser
    } finally {
      initialized.value = true;
    }
  }

  async function login(email: string, password: string) {
    isLoading.value = true;
    try {
      const tokens = await authApi.login({ email, password });
      setTokens(tokens.access_token, tokens.refresh_token);
      user.value = await authApi.getProfile();
    } finally {
      isLoading.value = false;
    }
  }

  async function register(email: string, password: string, username?: string, fullName?: string) {
    isLoading.value = true;
    try {
      await authApi.register({
        email,
        password,
        username,
        full_name: fullName,
      });
      await login(email, password);
    } finally {
      isLoading.value = false;
    }
  }

  async function logout() {
    window.localStorage.removeItem('access_token');
    window.localStorage.removeItem('refresh_token');
    user.value = null;

    try {
      await authApi.logout();
    } catch {
      // ignore server-side logout failures
    }
  }

  return {
    user,
    isLoading,
    initialized,
    isAuthenticated,
    setTokens,
    initialize,
    loadUser,
    login,
    register,
    logout,
  };
});
