import { useState } from 'react';
import { AuthProvider, useAuth } from './AuthContext';
import LoginPage from './LoginPage';
import RegisterPage from './RegisterPage';
import ForgotPasswordPage from './ForgotPasswordPage';
import ResetPasswordPage from './ResetPasswordPage';
import ProfilePage from './ProfilePage';
import Dashboard from './Dashboard';

function AppShell() {
  const { token } = useAuth();
  // 'login' | 'register' | 'forgot' | 'reset'
  const [authView, setAuthView] = useState('login');
  const [page, setPage] = useState('dashboard'); // 'dashboard' | 'profile'

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

  return page === 'profile' ? (
    <ProfilePage onBack={() => setPage('dashboard')} />
  ) : (
    <Dashboard onOpenProfile={() => setPage('profile')} />
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}
