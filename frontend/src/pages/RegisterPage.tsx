import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowRight, Lock, Mail, UserRound } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import AuthLayout from '../components/layout/AuthLayout';

const RegisterPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const register = useAuthStore((state) => state.register);
  const isLoading = useAuthStore((state) => state.isLoading);
  const navigate = useNavigate();

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');

    try {
      await register(email, password, username || undefined, fullName || undefined);
      navigate('/');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed. Please try again.');
    }
  };

  return (
    <AuthLayout
      eyebrow="Create account"
      title="Set up your research workspace"
      description="Create a secure LiRA account to launch reviews, monitor every stage, and keep approval decisions visible to your team."
    >
      {error && (
        <div className="mb-5 flex items-start gap-3 rounded-2xl border border-accent-rose/20 bg-accent-rose/10 px-4 py-3 text-sm text-accent-rose">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="register-fullname" className="field-label">
              Full name
            </label>
            <div className="relative">
              <UserRound className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
              <input
                id="register-fullname"
                type="text"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                className="input-dark pl-11"
                placeholder="Jane Doe"
              />
            </div>
          </div>

          <div>
            <label htmlFor="register-username" className="field-label">
              Username
            </label>
            <input
              id="register-username"
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="input-dark"
              placeholder="janedoe"
            />
          </div>
        </div>

        <div>
          <label htmlFor="register-email" className="field-label">
            Email
          </label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
            <input
              id="register-email"
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
            <label htmlFor="register-password" className="field-label mb-0">
              Password
            </label>
            <span className="text-xs text-gray-500">Minimum 8 characters</span>
          </div>
          <div className="relative">
            <Lock className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
            <input
              id="register-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="input-dark pl-11"
              placeholder="Create a strong password"
              minLength={8}
              required
            />
          </div>
        </div>

        <button
          id="register-submit"
          type="submit"
          disabled={isLoading}
          className="btn-primary w-full"
        >
          {isLoading ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              Creating account
            </>
          ) : (
            <>
              Create account
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
      </form>

      <div className="mt-6 rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3 text-sm text-gray-400">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-white hover:text-accent-cyan">
          Sign in
        </Link>
      </div>
    </AuthLayout>
  );
};

export default RegisterPage;
