import { create } from 'zustand';
import { authApi, type User } from '../api/auth';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  setTokens: (accessToken: string, refreshToken: string) => void;
  loadUser: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, username?: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,

  setTokens: (accessToken, refreshToken) => {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    set({ isAuthenticated: true });
  },

  loadUser: async () => {
    if (!localStorage.getItem('access_token')) {
      set({ isAuthenticated: false, user: null });
      return;
    }
    set({ isLoading: true });
    try {
      const user = await authApi.getProfile();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  },

  login: async (email, password) => {
    set({ isLoading: true });
    try {
      const tokens = await authApi.login({ email, password });
      get().setTokens(tokens.access_token, tokens.refresh_token);
      const user = await authApi.getProfile();
      set({ user, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  register: async (email, password, username, fullName) => {
    set({ isLoading: true });
    try {
      await authApi.register({ email, password, username, full_name: fullName });
      // Auto-login after registration
      await get().login(email, password);
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ user: null, isAuthenticated: false });
    authApi.logout().catch(() => {});
  },
}));
