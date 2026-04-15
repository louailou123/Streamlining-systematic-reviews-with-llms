import client from './client';
import type { LoginRequest, RegisterRequest, TokenResponse, User } from '@/types/auth';

export const authApi = {
  async register(data: RegisterRequest): Promise<User> {
    const response = await client.post<User>('/auth/register', data);
    return response.data;
  },

  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await client.post<TokenResponse>('/auth/login', data);
    return response.data;
  },

  async getProfile(): Promise<User> {
    const response = await client.get<User>('/auth/me');
    return response.data;
  },

  async getGoogleLoginUrl(): Promise<string> {
    const response = await client.get<{ authorization_url: string }>('/auth/google/login');
    return response.data.authorization_url;
  },

  async logout(): Promise<void> {
    await client.post('/auth/logout');
  },
};
