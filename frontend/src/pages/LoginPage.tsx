import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowRight, Lock, Mail } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { authApi } from '../api/auth';
import AuthLayout from '../components/layout/AuthLayout';

const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const login = useAuthStore((state) => state.login);
  const isLoading = useAuthStore((state) => state.isLoading);
  const navigate = useNavigate();

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');

    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Login failed. Please try again.');
    }
  };

  const handleGoogleLogin = async () => {
    try {
      const url = await authApi.getGoogleLoginUrl();
      window.location.href = url;
    } catch {
      setError('Google login is not configured yet.');
    }
  };

  return (
    <AuthLayout
      eyebrow="Welcome back"
      title="Sign in to your LiRA workspace"
      description="Pick up your review where you left it, inspect live pipeline status, and move approved work forward without losing context."
    >
      {error && (
        <div className="mb-5 flex items-start gap-3 rounded-2xl border border-accent-rose/20 bg-accent-rose/10 px-4 py-3 text-sm text-accent-rose">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="login-email" className="field-label">
            Email
          </label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="input-dark pl-11"
              placeholder="you@example.com"
              required
            />
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between gap-3">
            <label htmlFor="login-password" className="field-label mb-0">
              Password
            </label>
            <span className="text-xs text-gray-500">Secure email sign-in</span>
          </div>
          <div className="relative">
            <Lock className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="input-dark pl-11"
              placeholder="Enter your password"
              required
            />
          </div>
        </div>

        <button
          id="login-submit"
          type="submit"
          disabled={isLoading}
          className="btn-primary w-full"
        >
          {isLoading ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              Signing in
            </>
          ) : (
            <>
              Sign in
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
      </form>

      <div className="my-6 flex items-center gap-3">
        <div className="h-px flex-1 bg-white/8" />
        <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">or</span>
        <div className="h-px flex-1 bg-white/8" />
      </div>

      <button type="button" onClick={handleGoogleLogin} className="btn-secondary w-full">
        <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
        </svg>
        Continue with Google
      </button>

      <div className="mt-6 rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3 text-sm text-gray-400">
        New to LiRA?{' '}
        <Link to="/register" className="font-semibold text-white hover:text-accent-cyan">
          Create your account
        </Link>
      </div>
    </AuthLayout>
  );
};

export default LoginPage;
