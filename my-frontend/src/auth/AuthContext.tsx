import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config';

// Define types
interface User {
  id: string;
  name: string;
  email: string;
  google_id?: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  loading: boolean;
  error: string | null;
  login: () => void;
  handleOAuthCallback: (token: string, userId: string) => Promise<void>;
  logout: () => void;
}

// Create context with default values
const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  user: null,
  loading: true,
  error: null,
  login: () => {},
  handleOAuthCallback: async () => {},
  logout: () => {},
});

// Custom hook to use the auth context
export const useAuth = () => useContext(AuthContext);

// Provider component
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check if user is already authenticated on mount
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      fetchUserData(token);
    } else {
      setLoading(false);
    }
  }, []);

  // Function to fetch user data using token
  const fetchUserData = async (token: string) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/auth/user`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      setUser(response.data.user);
      setIsAuthenticated(true);
      setError(null);
    } catch (err) {
      console.error('Error fetching user data:', err);
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_id');
      setError('Session expired. Please log in again.');
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  // Start OAuth flow
  const login = () => {
    // Open Google OAuth page
    window.location.href = `${API_URL}/auth/google/login`;
  };

  // Process OAuth callback
  const handleOAuthCallback = async (token: string, userId: string) => {
    localStorage.setItem('auth_token', token);
    localStorage.setItem('user_id', userId);
    await fetchUserData(token);
  };

  // Logout function
  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_id');
    setUser(null);
    setIsAuthenticated(false);
    
    // Redirect to home page
    window.location.href = '/';
  };

  // Context value
  const contextValue: AuthContextType = {
    isAuthenticated,
    user,
    loading,
    error,
    login,
    handleOAuthCallback,
    logout
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext; 