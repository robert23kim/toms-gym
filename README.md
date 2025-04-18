# Tom's Gym

A platform for fitness competitions, video uploads, and weightlifting challenges.

## Project Structure

- **Backend/**: Python Flask API for video handling and competition management
- **my-frontend/**: React/TypeScript frontend application
- **tests/**: Mobile video playback testing scripts and tools
- **docker-compose.yml**: Orchestrates the development environment

## 🚀 Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- [Node.js](https://nodejs.org/) (for frontend development)
- [Python 3.11+](https://www.python.org/downloads/) (for backend development)
- Google Cloud credentials for storage access (for production)

### Local Development Environment

The easiest way to run the entire application locally is using Docker Compose:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

This will start:
- Backend API on http://localhost:8888
- Frontend on http://localhost:8081
- Test server on http://localhost:8000

### Manual Setup (Alternative)

#### Backend Setup

```bash
cd Backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Set required environment variables
export USE_MOCK_DB=true
export DATABASE_URL=sqlite:///test.db
export GCS_BUCKET=jtr-lift-u-4ever-cool-bucket
export FLASK_ENV=development
export FLASK_DEBUG=1

# Run the application
python main.py
```

#### Frontend Setup

```bash
cd my-frontend

# Install dependencies
npm install

# Create .env.development file with:
echo "VITE_API_URL=http://localhost:8888" > .env.development

# Start development server
npm run dev
```

## 🧪 Testing

### Run Backend Tests

```bash
cd Backend
python -m pytest
```

### Run Mobile Video Tests

```bash
cd tests
./run-mobile-tests.sh
```

## 📱 Mobile Compatibility

The application has been specially optimized for mobile video playback with:

- Direct video streaming from the backend
- Proper handling of range requests for efficient mobile playback
- Compatible with iOS and Android browsers

## 🌎 Deployment

### Deploy to Google Cloud Run

```bash
# Deploy both frontend and backend
python deploy.py

# Deploy only backend
python deploy.py --backend-only

# Deploy only frontend
python deploy.py --frontend-only

# Set custom API URL for frontend
python deploy.py --api-url https://my-api.example.com
```

### Environment Variables

#### Backend Environment Variables
- `FLASK_ENV`: Set to 'production' for deployment
- `DB_INSTANCE`: Cloud SQL instance connection name
- `DB_USER`: Database username
- `DB_PASS`: Database password
- `DB_NAME`: Database name
- `GCS_BUCKET`: Google Cloud Storage bucket name

#### Frontend Environment Variables
- `VITE_API_URL`: URL to the backend API

## 🔧 Troubleshooting

### Database Connectivity Issues

If you encounter database connectivity issues, check:
1. Environment variables are correctly set
2. For local development, ensure `USE_MOCK_DB=true` and `DATABASE_URL` are set
3. For production, ensure `DB_INSTANCE`, `DB_USER`, `DB_PASS`, and `DB_NAME` are set

### Mobile Video Playback Issues

If videos don't play correctly on mobile:
1. Check the backend logs for errors
2. Ensure the backend can access the GCS bucket
3. Run the mobile tests to identify specific issues: `./tests/run-mobile-tests.sh`

## 🧰 Maintenance

### Update Dependencies

```bash
# Update backend dependencies
cd Backend
pip install --upgrade -r requirements.txt

# Update frontend dependencies
cd my-frontend
npm update
```

## 📄 License

Copyright © 2025 Tom's Gym

## OAuth Authentication Setup

Tom's Gym now supports Google OAuth authentication!

### Configuration

1. Set up a Google OAuth client:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or use an existing one
   - Navigate to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Set the Application type to "Web application"
   - Add authorized redirect URIs: `http://localhost:9888/auth/callback` (for local development)
   - Copy the Client ID and Client Secret

2. Configure environment variables:
   - Create a `.env` file in the project root or set these environment variables:
   ```
   OAUTH_CLIENT_ID=your_google_client_id
   OAUTH_CLIENT_SECRET=your_google_client_secret
   OAUTH_REDIRECT_URI=http://localhost:3000/auth/callback
   APP_SECRET_KEY=your_secret_key
   ```

### Running with OAuth

1. Start Docker on your machine

2. Start the application with OAuth support:
   ```
   docker-compose up -d
   ```

3. Test the OAuth flow:
   - Visit the frontend at http://localhost:3000
   - Click "Login" and then "Sign in with Google"
   - You'll be redirected to Google's authentication page
   - After signing in, you'll be redirected back to the app

### For Testing/Development

For testing purposes, you can use the mock OAuth endpoint:

```bash
curl -X POST http://localhost:9888/auth/mock/callback \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","name":"Test User"}'
```

This will return a valid token that can be used for testing the authenticated endpoints.