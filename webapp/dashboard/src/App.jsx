import './Account.css';
import { useState } from 'react';
import { AuthProvider, useAuth } from './AuthContext';
import LoginPage from './LoginPage';
import RegisterPage from './RegisterPage';
import ForgotPasswordPage from './ForgotPasswordPage';
import ResetPasswordPage from './ResetPasswordPage';
import ProfilePage from './ProfilePage';
import Dashboard from './Dashboard';
import AdminPage from './AdminPage';

function AppShell() {
  const { token, authReady, user } = useAuth();
  // 'login' | 'register' | 'forgot' | 'reset'
  const [authView, setAuthView] = useState('login');
  const [page, setPage] = useState('dashboard'); // 'dashboard' | 'profile' | 'admin'

  if (!authReady) {
    return (
      <div className="session-check-page">
        <div className="session-check-card">
          <span className="session-spinner" aria-hidden="true" />
          <span className="auth-eyebrow">Secure session</span>
          <h1>Checking your account</h1>
          <p>Connecting to the selected Stress Monitor API…</p>
        </div>
      </div>
    );
  }

  if (!token) {
    if (authView === 'register') {
      return <RegisterPage onSwitchToLogin={() => setAuthView('login')} />;
    }
    if (authView === 'forgot') {
      return (
        <ForgotPasswordPage
          onSwitchToLogin={() => setAuthView('login')}
          onGotCode={() => setAuthView('reset')}
        />
      );
    }
    if (authView === 'reset') {
      return <ResetPasswordPage onSwitchToLogin={() => setAuthView('login')} />;
    }
    return (
      <LoginPage
        onSwitchToRegister={() => setAuthView('register')}
        onForgotPassword={() => setAuthView('forgot')}
      />
    );
  }

  if (page === 'profile') {
    return <ProfilePage onBack={() => setPage('dashboard')} />;
  }

  if (page === 'admin' && user?.is_admin) {
    return <AdminPage onBack={() => setPage('dashboard')} />;
  }

  return (
    <Dashboard
      onOpenProfile={() => setPage('profile')}
      onOpenAdmin={() => setPage('admin')}
    />
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}
