import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { Sparkles } from 'lucide-react';

const OAuthCallbackPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const setTokens = useAuthStore((s) => s.setTokens);
  const loadUser = useAuthStore((s) => s.loadUser);
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
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center animate-fade-in">
        <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center animate-pulse-glow">
          <Sparkles className="w-8 h-8 text-white" />
        </div>
        <p className="text-gray-400">Completing sign in...</p>
      </div>
    </div>
  );
};

export default OAuthCallbackPage;
