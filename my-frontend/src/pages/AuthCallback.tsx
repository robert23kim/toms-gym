import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

const AuthCallback: React.FC = () => {
  const location = useLocation();
  const { handleOAuthCallback } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const processAuth = async () => {
      // Get query parameters from URL
      const searchParams = new URLSearchParams(location.search);
      const token = searchParams.get('token');
      const userId = searchParams.get('user_id');
      const errorMsg = searchParams.get('error');

      if (errorMsg) {
        setError(errorMsg);
        // Redirect to error page after a brief delay
        setTimeout(() => {
          window.location.href = `/auth/error?message=${encodeURIComponent(errorMsg)}`;
        }, 1500);
        return;
      }

      if (!token || !userId) {
        setError('Authentication failed: Missing token or user ID');
        setTimeout(() => {
          window.location.href = '/auth/error?message=Missing token or user ID';
        }, 1500);
        return;
      }

      try {
        // Process authentication
        await handleOAuthCallback(token, userId);
        // Redirect to home page
        window.location.href = '/';
      } catch (err) {
        console.error('Error processing authentication:', err);
        setError('Failed to complete authentication');
        setTimeout(() => {
          window.location.href = '/auth/error?message=Failed to complete authentication';
        }, 1500);
      }
    };

    processAuth();
  }, [location, handleOAuthCallback]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      {error ? (
        <div className="p-6 bg-red-100 rounded-lg shadow-md">
          <h2 className="text-xl text-red-700 font-semibold mb-2">Authentication Error</h2>
          <p className="text-red-600">{error}</p>
          <p className="mt-4 text-sm text-gray-600">Redirecting to error page...</p>
        </div>
      ) : (
        <div className="flex flex-col items-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="mt-4 text-lg">Completing authentication...</p>
        </div>
      )}
    </div>
  );
};

export default AuthCallback; 