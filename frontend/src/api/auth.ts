import client from './client';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  username?: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  username: string | null;
  full_name: string | null;
  avatar_url: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

export const authApi = {
  async register(data: RegisterRequest): Promise<User> {
    const res = await client.post('/auth/register', data);
    return res.data;
  },

  async login(data: LoginRequest): Promise<TokenResponse> {
    const res = await client.post('/auth/login', data);
    return res.data;
  },

  async getProfile(): Promise<User> {
    const res = await client.get('/auth/me');
    return res.data;
  },

  async getGoogleLoginUrl(): Promise<string> {
    const res = await client.get('/auth/google/login');
    return res.data.authorization_url;
  },

  async logout(): Promise<void> {
    await client.post('/auth/logout');
  },
};
