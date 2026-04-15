import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { LoaderCircle } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import AuthLayout from '../components/layout/AuthLayout';

const OAuthCallbackPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const setTokens = useAuthStore((state) => state.setTokens);
  const loadUser = useAuthStore((state) => state.loadUser);
  const navigate = useNavigate();

  useEffect(() => {
    const accessToken = searchParams.get('access_token');
    const refreshToken = searchParams.get('refresh_token');

    if (accessToken && refreshToken) {
      setTokens(accessToken, refreshToken);
      loadUser().then(() => navigate('/'));
    } else {
      navigate('/login');
    }
  }, [searchParams, setTokens, loadUser, navigate]);

  return (
    <AuthLayout
      eyebrow="Connecting account"
      title="Completing your sign-in"
      description="We are finalizing your session and preparing your LiRA workspace."
    >
      <div className="flex flex-col items-center justify-center rounded-3xl border border-white/8 bg-white/[0.03] px-6 py-14 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full border border-white/10 bg-dark-surface-2">
          <LoaderCircle className="h-7 w-7 animate-spin text-accent-blue-light" />
        </div>
        <h2 className="mt-6 text-xl font-semibold text-white">Signing you in</h2>
        <p className="mt-3 max-w-sm text-sm leading-6 text-gray-400">
          Your account has been verified. LiRA will redirect you to the dashboard as soon as your profile is ready.
        </p>
      </div>
    </AuthLayout>
  );
};

export default OAuthCallbackPage;
