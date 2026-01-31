import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { X, Search, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config';

interface FindProfileProps {
  onClose: () => void;
}

const FindProfile: React.FC<FindProfileProps> = ({ onClose }) => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email) {
      setError('Please enter your email address');
      return;
    }

    setLoading(true);
    setError(null);
    setNotFound(false);

    try {
      const response = await axios.get(`${API_URL}/users/by-email/${encodeURIComponent(email)}`);

      if (response.data && response.data.id) {
        // Store userId in localStorage for future use
        localStorage.setItem('userId', response.data.id);

        // Navigate to profile
        onClose();
        navigate(`/profile/${response.data.id}`);
      }
    } catch (err) {
      const axiosErr = err as { response?: { status?: number } };
      if (axiosErr.response?.status === 404) {
        setNotFound(true);
      } else {
        setError('Failed to look up profile. Please try again.');
      }
    } finally {
      setLoading(false);
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
        className="bg-background rounded-xl shadow-lg w-full max-w-md p-6 relative"
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors"
        >
          <X size={20} />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Search className="w-5 h-5 text-primary" />
          </div>
          <h2 className="text-xl font-semibold">Find Your Profile</h2>
        </div>

        <p className="text-muted-foreground mb-4">
          Enter the email address you used when uploading videos to find your profile.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setError(null);
                setNotFound(false);
              }}
              placeholder="your@email.com"
              className="w-full px-3 py-2 rounded-md border border-border bg-background"
              autoFocus
            />
          </div>

          {error && (
            <div className="bg-red-100 text-red-700 p-3 rounded text-sm">{error}</div>
          )}

          {notFound && (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 p-4 rounded">
              <p className="font-medium mb-2">No profile found with that email</p>
              <p className="text-sm mb-3">
                Would you like to create a profile? You can also upload a video directly and your profile will be created automatically.
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    navigate('/upload');
                  }}
                  className="flex-1 px-3 py-2 bg-primary text-primary-foreground rounded text-sm hover:bg-primary/90"
                >
                  Upload a Video
                </button>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !email}
            className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              'Searching...'
            ) : (
              <>
                <User size={18} />
                Find My Profile
              </>
            )}
          </button>
        </form>
      </motion.div>
    </motion.div>
  );
};

export default FindProfile;
