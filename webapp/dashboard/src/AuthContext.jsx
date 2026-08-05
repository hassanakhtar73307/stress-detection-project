import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import axios from 'axios';

import { API_BASE } from './api';

const AuthContext = createContext(null);
const TOKEN_KEY = 'sd_token';

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [authReady, setAuthReady] = useState(false);

  const clearSession = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
  }, []);

  const persist = useCallback((newToken, newUser) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem(TOKEN_KEY, newToken);
  }, []);

  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);

    if (!storedToken) {
      setAuthReady(true);
      return undefined;
    }

    let active = true;

    axios.get(`${API_BASE}/profile`, {
      headers: { Authorization: `Bearer ${storedToken}` },
      timeout: 15000,
    })
      .then((response) => {
        if (!active) return;
        persist(storedToken, response.data);
      })
      .catch(() => {
        if (!active) return;
        clearSession();
      })
      .finally(() => {
        if (active) setAuthReady(true);
      });

    return () => {
      active = false;
    };
  }, [clearSession, persist]);

  const register = useCallback(async ({
    name,
    email,
    password,
    age,
    occupation,
    user_type,
    primary_goal,
    wearable_device,
    research_notice_acknowledged,
  }) => {
    const response = await axios.post(
      `${API_BASE}/register`,
      {
        name,
        email,
        password,
        age,
        occupation,
        user_type,
        primary_goal,
        wearable_device,
        research_notice_acknowledged,
      },
      { timeout: 20000 },
    );

    persist(response.data.token, response.data.user);
    return response.data.user;
  }, [persist]);

  const login = useCallback(async ({ email, password }) => {
    const response = await axios.post(
      `${API_BASE}/login`,
      { email, password },
      { timeout: 20000 },
    );

    persist(response.data.token, response.data.user);
    return response.data.user;
  }, [persist]);

  const logout = useCallback(() => {
    clearSession();
  }, [clearSession]);

  const updateProfile = useCallback(async ({
    name,
    age,
    occupation,
    user_type,
    primary_goal,
    wearable_device,
  }) => {
    if (!token) throw new Error('You are not signed in.');

    try {
      const response = await axios.put(
        `${API_BASE}/profile`,
        {
          name,
          age,
          occupation,
          user_type,
          primary_goal,
          wearable_device,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 20000,
        },
      );

      setUser(response.data);
      return response.data;
    } catch (error) {
      if (error.response?.status === 401) clearSession();
      throw error;
    }
  }, [clearSession, token]);

  const authHeader = useMemo(
    () => (token ? { Authorization: `Bearer ${token}` } : {}),
    [token],
  );

  const value = useMemo(() => ({
    token,
    user,
    authReady,
    register,
    login,
    logout,
    updateProfile,
    authHeader,
  }), [
    token,
    user,
    authReady,
    register,
    login,
    logout,
    updateProfile,
    authHeader,
  ]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
