import { useState } from 'react';
import { AuthProvider, useAuth } from './AuthContext';
import LoginPage from './LoginPage';
import RegisterPage from './RegisterPage';
import ProfilePage from './ProfilePage';
import Dashboard from './Dashboard';

function AppShell() {
  const { token } = useAuth();
  const [authView, setAuthView] = useState('login'); // 'login' | 'register'
  const [page, setPage] = useState('dashboard'); // 'dashboard' | 'profile'

  if (!token) {
    return authView === 'login' ? (
      <LoginPage onSwitchToRegister={() => setAuthView('register')} />
    ) : (
      <RegisterPage onSwitchToLogin={() => setAuthView('login')} />
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
