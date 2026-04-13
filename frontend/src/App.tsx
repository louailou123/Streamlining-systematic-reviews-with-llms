import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import OAuthCallbackPage from './pages/OAuthCallbackPage';
import DashboardPage from './pages/DashboardPage';
import ResearchWorkspace from './pages/ResearchWorkspace';

const App: React.FC = () => {
  const loadUser = useAuthStore((s) => s.loadUser);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={
          isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />
        } />
        <Route path="/register" element={
          isAuthenticated ? <Navigate to="/" replace /> : <RegisterPage />
        } />
        <Route path="/auth/callback" element={<OAuthCallbackPage />} />

        {/* Protected routes */}
        <Route path="/" element={
          <ProtectedRoute><DashboardPage /></ProtectedRoute>
        } />
        <Route path="/research/:id" element={
          <ProtectedRoute><ResearchWorkspace /></ProtectedRoute>
        } />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
