import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

interface PasswordResetFormProps {
    onSuccess?: () => void;
    onError?: (error: string) => void;
}

export const PasswordResetForm: React.FC<PasswordResetFormProps> = ({ onSuccess, onError }) => {
    const [searchParams] = useSearchParams();
    const token = searchParams.get('token');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isRequestSent, setIsRequestSent] = useState(false);
    const navigate = useNavigate();

    const validatePassword = (password: string) => {
        if (password.length < 8) {
            setError('Password must be at least 8 characters long');
            return false;
        }
        if (!/[A-Z]/.test(password)) {
            setError('Password must contain at least one uppercase letter');
            return false;
        }
        if (!/[a-z]/.test(password)) {
            setError('Password must contain at least one lowercase letter');
            return false;
        }
        if (!/[0-9]/.test(password)) {
            setError('Password must contain at least one number');
            return false;
        }
        if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
            setError('Password must contain at least one special character');
            return false;
        }
        return true;
    };

    const handleRequestSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!email) {
            setError('Please enter your email address');
            return;
        }

        setIsLoading(true);

        try {
            const response = await fetch(`${process.env.REACT_APP_API_URL}/auth/password-reset-request`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to send reset request');
            }

            setIsRequestSent(true);
            if (onSuccess) {
                onSuccess();
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to send reset request';
            setError(errorMessage);
            if (onError) {
                onError(errorMessage);
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleResetSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!token) {
            setError('Invalid reset token');
            return;
        }

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        if (!validatePassword(password)) {
            return;
        }

        setIsLoading(true);

        try {
            const response = await fetch(`${process.env.REACT_APP_API_URL}/auth/password-reset`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    token,
                    new_password: password
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to reset password');
            }

            if (onSuccess) {
                onSuccess();
            }
            navigate('/login');
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to reset password';
            setError(errorMessage);
            if (onError) {
                onError(errorMessage);
            }
        } finally {
            setIsLoading(false);
        }
    };

    if (isRequestSent) {
        return (
            <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md text-center">
                <h2 className="text-2xl font-bold mb-4">Reset Email Sent</h2>
                <p className="text-gray-600 mb-4">
                    We've sent a password reset link to your email address. Please check your inbox and follow the instructions.
                </p>
                <button
                    onClick={() => navigate('/login')}
                    className="text-blue-600 hover:text-blue-500"
                >
                    Return to Login
                </button>
            </div>
        );
    }

    if (token) {
        return (
            <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
                <h2 className="text-2xl font-bold mb-6 text-center">Reset Password</h2>
                
                {error && (
                    <div className="mb-4 p-3 bg-red-100 text-red-700 rounded">
                        {error}
                    </div>
                )}

                <form onSubmit={handleResetSubmit} className="space-y-4">
                    <div>
                        <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                            New Password
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

                    <div>
                        <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                            Confirm New Password
                        </label>
                        <input
                            type="password"
                            id="confirmPassword"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                            required
                        />
                    </div>

                    <div>
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
                        >
                            {isLoading ? 'Resetting password...' : 'Reset Password'}
                        </button>
                    </div>
                </form>
            </div>
        );
    }

    return (
        <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
            <h2 className="text-2xl font-bold mb-6 text-center">Reset Password</h2>
            
            {error && (
                <div className="mb-4 p-3 bg-red-100 text-red-700 rounded">
                    {error}
                </div>
            )}

            <form onSubmit={handleRequestSubmit} className="space-y-4">
                <div>
                    <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                        Email Address
                    </label>
                    <input
                        type="email"
                        id="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                        required
                    />
                </div>

                <div>
                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
                    >
                        {isLoading ? 'Sending reset link...' : 'Send Reset Link'}
                    </button>
                </div>

                <div className="text-center mt-4">
                    <p className="text-sm text-gray-600">
                        Remember your password?{' '}
                        <a href="/login" className="text-blue-600 hover:text-blue-500">
                            Login
                        </a>
                    </p>
                </div>
            </form>
        </div>
    );
}; 