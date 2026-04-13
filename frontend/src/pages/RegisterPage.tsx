import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { Sparkles, ArrowRight, Mail, Lock, User, AlertCircle } from 'lucide-react';

const RegisterPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const register = useAuthStore((s) => s.register);
  const isLoading = useAuthStore((s) => s.isLoading);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await register(email, password, username || undefined, fullName || undefined);
      navigate('/');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed. Please try again.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-accent-purple/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 left-1/3 w-80 h-80 bg-accent-cyan/10 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md animate-fade-in">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-3xl font-bold gradient-text">LiRA</h1>
          </div>
          <p className="text-gray-400 text-sm">Create your research account</p>
        </div>

        <div className="glass-card p-8">
          <h2 className="text-xl font-semibold text-gray-100 mb-6">Get started</h2>

          {error && (
            <div className="flex items-center gap-2 p-3 mb-4 bg-accent-rose/10 border border-accent-rose/20 rounded-lg text-accent-rose text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Full name</label>
                <input
                  id="register-fullname"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="input-dark"
                  placeholder="John Doe"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Username</label>
                <input
                  id="register-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input-dark"
                  placeholder="johndoe"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  id="register-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-dark pl-10"
                  placeholder="you@example.com"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  id="register-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-dark pl-10"
                  placeholder="Min. 8 characters"
                  minLength={8}
                  required
                />
              </div>
            </div>

            <button
              id="register-submit"
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>Create account <ArrowRight className="w-4 h-4" /></>
              )}
            </button>
          </form>

          <p className="text-center text-sm text-gray-500 mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-accent-blue hover:text-accent-blue-light transition-colors">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
