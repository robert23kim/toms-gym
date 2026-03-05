import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { X } from 'lucide-react';
import axios from 'axios';
import { API_URL } from '../config';
import { useAuth } from '../auth/AuthContext';

interface LoginProps {
  onClose: () => void;
  onSubmit: (loginData: any) => Promise<void>;
}

const Login: React.FC<LoginProps> = ({ onClose, onSubmit }) => {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });

  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string>('');
  const { handleLoginSuccess } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');
    setIsLoading(true);
    
    try {
      // Direct API call to backend login endpoint
      const response = await axios.post(
        `${API_URL}/auth/login`,
        formData
      );
      
      if (response.status === 200) {
        // Store auth token and user ID
        localStorage.setItem('auth_token', response.data.access_token);
        localStorage.setItem('userId', response.data.user_id);
        
        // Update auth context
        await handleLoginSuccess(response.data.access_token, response.data.user_id);
        
        setSuccessMessage('Login successful!');
        
        // Short delay to show success message before closing
        setTimeout(() => {
          onClose();
        }, 1000);
      }
    } catch (err: any) {
      console.error('Error logging in:', err);
      setError(err.response?.data?.error || 'Invalid username or password. Please try again.');
      setFormData(prev => ({
        ...prev,
        password: ''
      }));
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="bg-background rounded-xl shadow-lg w-full max-w-md p-6 relative"
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors"
        >
          <X size={20} />
        </button>

        <h2 className="text-2xl font-semibold mb-6">Login</h2>

        {successMessage && <div className="bg-green-100 text-green-700 p-3 rounded mb-4">{successMessage}</div>}
        {error && <div className="bg-red-100 text-red-700 p-3 rounded mb-4">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 rounded-md border border-border bg-background"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 rounded-md border border-border bg-background"
            />
          </div>

          <div className="flex gap-3 mt-6">
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-accent text-white rounded-md hover:bg-accent/90 transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Logging in...' : 'Login'}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-secondary text-foreground rounded-md hover:bg-secondary/70 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
};

export default Login; 