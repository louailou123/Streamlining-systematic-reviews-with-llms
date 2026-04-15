import React from 'react';
import { Navigate } from 'react-router-dom';
import { LoaderCircle } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import AppLogo from '../ui/AppLogo';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isLoading = useAuthStore((state) => state.isLoading);

  if (isLoading && isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="panel-strong w-full max-w-md p-8 text-center">
          <div className="flex justify-center">
            <AppLogo subtitle="Secure workspace" />
          </div>
          <div className="mt-8 flex justify-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full border border-white/10 bg-dark-surface-2">
              <LoaderCircle className="h-6 w-6 animate-spin text-accent-blue-light" />
            </div>
          </div>
          <h1 className="mt-6 text-xl font-semibold text-white">Loading your workspace</h1>
          <p className="mt-2 text-sm leading-6 text-gray-400">
            Restoring your session and fetching the latest research state.
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};
