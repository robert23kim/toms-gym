import React, { useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { useNavigate } from 'react-router-dom';
import { API_URL } from '../config';

interface LoginFormProps {
    onSuccess?: () => void;
    onError?: (error: string) => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSuccess, onError }) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const { handleLoginSuccess } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSuccessMessage(null);
        setIsLoading(true);

        // Debug the API URL
        console.log('API URL:', API_URL);
        console.log('API URL type:', typeof API_URL);
        console.log('Environment variables:', import.meta.env);

        try {
            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            });

            // Debug the response
            console.log('Response status:', response.status);
            
            const data = await response.json();
            console.log('Response data:', data);

            if (!response.ok) {
                throw new Error(data.error || 'Login failed');
            }

            setSuccessMessage('Login successful! Redirecting...');
            
            // Use the handleLoginSuccess method from AuthContext with all tokens
            await handleLoginSuccess(data.access_token, data.refresh_token, data.user_id);
            console.log('Authentication state updated');

            if (onSuccess) {
                onSuccess();
            }
            
            // Short delay to show success message before redirect
            setTimeout(() => {
                navigate('/');
            }, 1000);
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Login failed';
            setError(errorMessage);
            setPassword(''); // Clear password field on error
            if (onError) {
                onError(errorMessage);
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
            <h2 className="text-2xl font-bold mb-6 text-center">Login</h2>
            
            {successMessage && (
                <div className="mb-4 p-3 bg-green-100 text-green-700 rounded">
                    {successMessage}
                </div>
            )}
            
            {error && (
                <div className="mb-4 p-3 bg-red-100 text-red-700 rounded">
                    {error}
                </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                        Username or Email
                    </label>
                    <input
                        type="text"
                        id="username"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                        required
                    />
                </div>

                <div>
                    <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                        Password
                    </label>
                    <input
                        type="password"
                        id="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                        required
                    />
                </div>

                <div className="flex items-center justify-between">
                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
                    >
                        {isLoading ? 'Logging in...' : 'Login'}
                    </button>
                </div>

                <div className="text-center mt-4">
                    <a
                        href="/forgot-password"
                        className="text-sm text-blue-600 hover:text-blue-500"
                    >
                        Forgot your password?
                    </a>
                </div>
            </form>
        </div>
    );
}; 