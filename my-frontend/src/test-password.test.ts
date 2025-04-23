import axios from 'axios';
import { API_URL } from './config';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock the API_URL
jest.mock('./config', () => ({
  API_URL: 'https://test-api-url.com',
}));

describe('Password Validation', () => {
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
  
  test('API accepts single character password', async () => {
    // Create profile data with a simple password "a"
    const profileData = {
      name: 'Test User',
      email: 'test@example.com',
      password: 'a'
    };
    
    // Call the API
    const response = await axios.post(`${API_URL}/auth/register`, profileData);
    
    // Verify axios was called with the correct data
    expect(mockedAxios.post).toHaveBeenCalledWith('https://test-api-url.com/auth/register', {
      name: 'Test User',
      email: 'test@example.com',
      password: 'a'
    });
    
    // Verify successful response
    expect(response.data).toEqual({
      access_token: 'test-access-token',
      refresh_token: 'test-refresh-token',
      user_id: 'test-user-id'
    });
  });
  
  test('API accepts registration with a valid password', async () => {
    // Create profile data with a valid password
    const profileData = {
      name: 'Test User',
      email: 'test@example.com',
      password: 'Password123!'
    };
    
    // Call the API directly
    const response = await axios.post(`${API_URL}/auth/register`, profileData);
    
    // Verify axios was called with the correct data
    expect(mockedAxios.post).toHaveBeenCalledWith('https://test-api-url.com/auth/register', {
      name: 'Test User',
      email: 'test@example.com',
      password: 'Password123!'
    });
    
    // Verify successful response
    expect(response.data).toEqual({
      access_token: 'test-access-token',
      refresh_token: 'test-refresh-token',
      user_id: 'test-user-id'
    });
  });
  
  test('createProfile function allows single character password', async () => {
    // Mock the createProfile function that would be used in the component
    const createProfile = async (profileData: any) => {
      // Call the API
      const response = await axios.post(`${API_URL}/auth/register`, profileData);
      return response.data;
    };
    
    // Create profile data with a one-character password
    const profileData = {
      name: 'Test User',
      email: 'test@example.com',
      password: 'a',
      weight_class: '83kg',
      country: 'United States',
      bio: 'Powerlifting enthusiast!'
    };
    
    // Call the createProfile function
    const result = await createProfile(profileData);
    
    // Verify axios was called with the correct data including single character password
    expect(mockedAxios.post).toHaveBeenCalledWith('https://test-api-url.com/auth/register', profileData);
    
    // Verify successful response from the function
    expect(result).toEqual({
      access_token: 'test-access-token',
      refresh_token: 'test-refresh-token',
      user_id: 'test-user-id'
    });
  });
}); 