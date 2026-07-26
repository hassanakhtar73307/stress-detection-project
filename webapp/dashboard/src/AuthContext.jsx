import { createContext, useContext, useState, useCallback } from 'react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:5000';
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('sd_token'));
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('sd_user');
    return stored ? JSON.parse(stored) : null;
  });

  const persist = (newToken, newUser) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem('sd_token', newToken);
    localStorage.setItem('sd_user', JSON.stringify(newUser));
  };

  const register = useCallback(async ({ name, email, password, age, occupation }) => {
    const res = await axios.post(`${API_BASE}/register`, { name, email, password, age, occupation });
    persist(res.data.token, res.data.user);
    return res.data.user;
  }, []);

  const login = useCallback(async ({ email, password }) => {
    const res = await axios.post(`${API_BASE}/login`, { email, password });
    persist(res.data.token, res.data.user);
    return res.data.user;
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('sd_token');
    localStorage.removeItem('sd_user');
  }, []);

  const updateProfile = useCallback(async ({ name, age, occupation }) => {
    const res = await axios.put(
      `${API_BASE}/profile`,
      { name, age, occupation },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    setUser(res.data);
    localStorage.setItem('sd_user', JSON.stringify(res.data));
    return res.data;
  }, [token]);

  const authHeader = token ? { Authorization: `Bearer ${token}` } : {};

  return (
    <AuthContext.Provider value={{ token, user, register, login, logout, updateProfile, authHeader }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
