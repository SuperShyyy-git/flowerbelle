import React, { createContext, useContext, useState, useEffect } from 'react';
import Cookies from 'js-cookie';
import api from '../services/api';
import toast from 'react-hot-toast';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = Cookies.get('access_token');
    
    if (token) {
      try {
        const response = await api.get('/auth/me/');
        setUser(response.data);
      } catch (error) {
        console.error('Auth check failed:', error);
        Cookies.remove('access_token');
        Cookies.remove('refresh_token');
      }
    }
    
    setLoading(false);
  };

  const login = async (username, password) => {
    try {
      const response = await api.post('/auth/login/', {
        username,
        password,
      });

      const { access, refresh, user: userData } = response.data;

      Cookies.set('access_token', access, { expires: 1 });
      Cookies.set('refresh_token', refresh, { expires: 7 });

      setUser(userData);
      toast.success(`Welcome back, ${userData.full_name}!`);
      
      return { success: true };
    } catch (error) {
      const message = error.response?.data?.detail || 'Login failed';
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout/');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      Cookies.remove('access_token');
      Cookies.remove('refresh_token');
      setUser(null);
      toast.success('Logged out successfully');
    }
  };

  const isOwner = () => user?.role === 'OWNER';
  const isStaff = () => user?.role === 'STAFF';

  const value = {
    user,
    loading,
    login,
    logout,
    isOwner,
    isStaff,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};