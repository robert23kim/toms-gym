import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import CreateProfile from './CreateProfile';
import { AuthProvider } from '../auth/AuthContext';

// Mock axios
jest.mock('axios');

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
    axios.post.mockResolvedValue({
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
    const nameInput = screen.getByLabelText(/name/i);
    fireEvent.change(nameInput, { target: { value: 'Test User' } });
    
    const emailInput = screen.getByLabelText(/email/i);
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    
    // Find password fields and set a single character password
    const passwordInputs = screen.getAllByLabelText(/password/i);
    const passwordInput = passwordInputs[0]; // First password field
    const confirmPasswordInput = passwordInputs[1]; // Confirm password field
    
    // Set both password fields to "a" (single character)
    fireEvent.change(passwordInput, { target: { value: 'a' } });
    fireEvent.change(confirmPasswordInput, { target: { value: 'a' } });
    
    // Submit the form
    const submitButton = screen.getByRole('button', { name: /create profile/i });
    fireEvent.click(submitButton);
    
    // Verify axios was called with the correct data including the single character password
    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith('https://test-api-url.com/auth/register', {
        name: 'Test User',
        email: 'test@example.com',
        password: 'a'
      });
    });
    
    // Check for success message
    await waitFor(() => {
      expect(screen.getByText(/profile created successfully/i)).toBeInTheDocument();
    });
    
    // Verify the component tries to close after success
    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
  });
}); 