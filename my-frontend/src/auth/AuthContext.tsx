import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config';
import { getAccessToken, getRefreshToken, getUserId, setTokens, clearTokens } from './tokenUtils';

// Define types
interface User {
  id: string;
  name: string;
  email: string;
  username?: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  loading: boolean;
  error: string | null;
  handleLoginSuccess: (accessToken: string, refreshToken: string, userId: string) => Promise<void>;
  logout: () => void;
}

// Create context with default values
const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  user: null,
  loading: true,
  error: null,
  handleLoginSuccess: async () => {},
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
    const token = getAccessToken();
    const userId = getUserId();
    
    if (token && userId) {
      fetchUserData(token);
    } else {
      // Try to use refresh token if available
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        refreshAccessToken(refreshToken);
      } else {
        setLoading(false);
      }
    }
  }, []);

  // Function to refresh the access token using refresh token
  const refreshAccessToken = async (refreshToken: string) => {
    try {
      setLoading(true);
      const response = await axios.post(`${API_URL}/auth/refresh`, {}, {
        headers: {
          Authorization: `Bearer ${refreshToken}`
        }
      });
      
      const { access_token, user_id } = response.data;
      
      // Update tokens, keeping the same refresh token
      setTokens(access_token, refreshToken, user_id);
      
      // Fetch user data with new access token
      await fetchUserData(access_token);
    } catch (err) {
      console.error('Error refreshing token:', err);
      clearTokens();
      setError('Session expired. Please log in again.');
      setIsAuthenticated(false);
      setLoading(false);
    }
  };

  // Function to fetch user data using token
  const fetchUserData = async (token: string) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/auth/user`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      setUser(response.data);
      setIsAuthenticated(true);
      setError(null);
    } catch (err) {
      console.error('Error fetching user data:', err);
      
      // Try to use refresh token if available
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        refreshAccessToken(refreshToken);
      } else {
        clearTokens();
        setError('Session expired. Please log in again.');
        setIsAuthenticated(false);
      }
    } finally {
      setLoading(false);
    }
  };

  // Handle successful password login
  const handleLoginSuccess = async (accessToken: string, refreshToken: string, userId: string) => {
    setTokens(accessToken, refreshToken, userId);
    await fetchUserData(accessToken);
  };

  // Logout function
  const logout = () => {
    // Call the logout API to blacklist the token if needed
    const token = getAccessToken();
    if (token) {
      axios.post(`${API_URL}/auth/logout`, {}, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }).catch(err => {
        console.error('Error during logout:', err);
      });
    }
    
    clearTokens();
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
    handleLoginSuccess,
    logout
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext; 