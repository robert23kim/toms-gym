import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import CreateProfile from './CreateProfile';
import { AuthProvider } from '../auth/AuthContext';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock the API_URL
jest.mock('../config', () => ({
  API_URL: 'https://test-api-url.com',
}));

describe('CreateProfile Password Validation', () => {
  const mockOnClose = jest.fn();
  const mockOnSubmit = jest.fn().mockResolvedValue(true);
  
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock successful registration response
    mockedAxios.post.mockResolvedValue({
      data: {
        access_token: 'test-access-token',
        refresh_token: 'test-refresh-token',
        user_id: 'test-user-id'
      }
    });
  });
  
  test('allows creation of profile with a single character password', async () => {
    // Render the component within AuthProvider for context
    render(
      <AuthProvider>
        <CreateProfile onClose={mockOnClose} onSubmit={mockOnSubmit} />
      </AuthProvider>
    );
    
    // Fill out the form with a one-character password
    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'Test User' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@example.com' } });

    // Password fields only render once "Set a password (optional)" is checked
    fireEvent.click(screen.getByLabelText(/set a password/i));

    // Set both password fields to "a" (single character)
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'a' } });
    fireEvent.change(screen.getByLabelText('Confirm Password'), { target: { value: 'a' } });
    
    // Submit the form
    const submitButton = screen.getByRole('button', { name: /create profile/i });
    fireEvent.click(submitButton);
    
    // Verify axios was called with the correct data including the single character password
    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith('https://test-api-url.com/auth/register', {
        name: 'Test User',
        email: 'test@example.com',
        password: 'a'
      });
    });
    
    // Check for success message
    await waitFor(() => {
      expect(screen.getByText(/profile created successfully/i)).toBeInTheDocument();
    });
    
    // Verify the component tries to close after success (closes via a 1.5s timeout)
    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    }, { timeout: 2500 });
  });
}); 