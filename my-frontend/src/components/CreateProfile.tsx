import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { X, Eye, EyeOff } from 'lucide-react';
import axios from 'axios';
import { API_URL } from '../config';
import { useAuth } from '../auth/AuthContext';

interface CreateProfileProps {
  onClose: () => void;
  onSubmit: (profileData: any) => Promise<boolean>;
}

const CreateProfile: React.FC<CreateProfileProps> = ({ onClose, onSubmit }) => {
  const { handleLoginSuccess } = useAuth();
  const [formData, setFormData] = useState({
    name: 'John Doe',
    email: 'john.doe@example.com',
    password: 'Password123',
    confirmPassword: 'Password123',
    weight_class: '83kg',
    country: 'United States',
    bio: 'Powerlifting enthusiast looking to compete and improve!'
  });

  const [message, setMessage] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate passwords match - this is the only validation we keep
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    
    setLoading(true);
    setError('');
    setMessage('');
    
    try {
      // Register the user using the auth endpoint
      const response = await axios.post(`${API_URL}/auth/register`, {
        name: formData.name,
        email: formData.email,
        password: formData.password
      });
      
      // Handle successful registration
      setMessage('Profile created successfully!');
      
      // Login the user automatically
      if (response.data.access_token && response.data.user_id) {
        // Use refresh token if available, otherwise use access token as refresh token too
        const refreshToken = response.data.refresh_token || response.data.access_token;
        handleLoginSuccess(response.data.access_token, refreshToken, response.data.user_id);
      }
      
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err: any) {
      console.error('Error creating profile:', err);
      // Show all error messages, including password-related ones
      const errorMsg = err.response?.data?.error || 'Failed to create profile. Please try again.';
      console.log('Full error message:', errorMsg);
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear any errors when changing password fields
    if (name === 'password' || name === 'confirmPassword') {
      setError('');
    }
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
        className="bg-background rounded-xl shadow-lg w-full max-w-md p-6 relative max-h-[90vh] overflow-y-auto"
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors"
        >
          <X size={20} />
        </button>

        <h2 className="text-2xl font-semibold mb-6">Create Profile</h2>

        {message && <div className="bg-green-100 text-green-700 p-3 rounded mb-4">{message}</div>}
        {error && <div className="bg-red-100 text-red-700 p-3 rounded mb-4">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 rounded-md border border-border bg-background"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 rounded-md border border-border bg-background"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 rounded-md border border-border bg-background"
              />
              <button 
                type="button"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Password validation disabled for testing purposes.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Confirm Password</label>
            <div className="relative">
              <input
                type={showConfirmPassword ? "text" : "password"}
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 rounded-md border border-border bg-background"
              />
              <button 
                type="button"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              >
                {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Weight Class</label>
            <select
              name="weight_class"
              value={formData.weight_class}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 rounded-md border border-border bg-background"
            >
              <option value="59kg">59kg</option>
              <option value="66kg">66kg</option>
              <option value="74kg">74kg</option>
              <option value="83kg">83kg</option>
              <option value="93kg">93kg</option>
              <option value="105kg">105kg</option>
              <option value="120kg">120kg</option>
              <option value="120kg+">120kg+</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Country</label>
            <input
              type="text"
              name="country"
              value={formData.country}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 rounded-md border border-border bg-background"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Bio</label>
            <textarea
              name="bio"
              value={formData.bio}
              onChange={handleChange}
              rows={3}
              className="w-full px-3 py-2 rounded-md border border-border bg-background"
            />
          </div>

          <div className="flex gap-3 mt-6">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-accent text-white rounded-md hover:bg-accent/90 transition-colors disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Profile'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-secondary text-foreground rounded-md hover:bg-secondary/70 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
};

export default CreateProfile; 