# OAuth Implementation for Tom's Gym

This document outlines the OAuth implementation for Tom's Gym application.

## Architecture

![OAuth Flow Diagram](https://www.plantuml.com/plantuml/png/VL9DIyD04BtlhnZIGrfWWH51WX8eA2In2JM8qOePQD9CjoRTTbnp6iiKP7sDhVxtylplljkDAuSf2Xar1a25AZ1ZF6NrGDwZK-2PAcXZM7Z5X0a3NeiQi4CeX_TUDbwKX1hLpXHfvSHH4HpBnAe-bfJoGkzwEqU-zPQwRTq_nKvs8v3JiP2cYGcqVLJ7Rr1nxhbqS_qRw6l1qZ1Mj9WkEwUFozcVxJcNR_f6SyrIMUl8Sv5AKwx9xYAkQw0RnwAYyZaY_d2NSTyZCVh-n-CnBbCK5BVoRu2yyGi0)

## Components

### Backend (Flask)

1. **auth_routes.py**
   - Google OAuth integration using Authlib
   - JWT token generation and validation
   - User profile endpoints
   - Mock OAuth endpoint for testing

2. **Database Integration**
   - User table with google_id field
   - JWT based authentication (stateless)

### Frontend (React)

1. **AuthContext.tsx**
   - Context provider for authentication state
   - Login, logout, and token handling

2. **Components**
   - GoogleLoginButton - Initiates OAuth flow
   - AuthCallback - Handles OAuth redirects
   - AuthError - Displays authentication errors

3. **Integration**
   - Login component with Google option
   - Protected routes using auth state

## Security Considerations

1. **JWT Security**
   - Tokens are signed with a secret key
   - Access token expiration: 7 days
   - Refresh token expiration: 90 days
   - HTTPS is required in production

2. **OAuth Security**
   - Client ID and Secret stored in environment variables
   - Validation of callback parameters
   - Error handling for authentication failures

3. **Data Protection**
   - Minimal user data stored (name, email, Google ID)
   - No passwords stored in our database

## Testing

1. **Manual Testing**
   - OAuth flow from frontend to Google and back
   - Error handling for various scenarios

2. **Automated Testing**
   - API endpoint tests
   - Mock OAuth flow for CI/CD
   - Integration tests with Puppeteer

## Deployment Considerations

1. **Environment Variables**
   - OAUTH_CLIENT_ID
   - OAUTH_CLIENT_SECRET
   - OAUTH_REDIRECT_URI
   - APP_SECRET_KEY

2. **Production Setup**
   - Update Google OAuth console with production redirect URIs
   - Enable HTTPS for all authentication traffic
   - Set appropriate CORS headers

## Implemented Security Features

The following security features are now implemented:

1. **Token Management**
   - Refresh tokens (90-day expiration)
   - Token blacklisting for logout/revocation
   - JWT-based stateless authentication

2. **Rate Limiting**
   - Login attempts: 100/day per IP
   - Registration attempts: 10/day per IP
   - Account lockout after 5 failed login attempts (15-minute duration)

## Future Improvements

1. **Additional OAuth Providers**
   - Implement Facebook, GitHub, Apple login
   - Unified provider interface

2. **User Management**
   - Account linking (connect multiple OAuth providers)
   - Profile management with OAuth data sync
   - Role-based access control