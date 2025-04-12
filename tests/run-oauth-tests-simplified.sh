#!/bin/bash

set -e  # Exit on any error

echo "🧪 Running Simplified OAuth Authentication Tests..."
echo "This script doesn't require a running backend and tests the structure only."

# Make sure test directories exist
mkdir -p test-results
mkdir -p screenshots

# Function to log test steps
log_step() {
  echo -e "\n🔍 $1"
}

# Check if key files exist
log_step "Checking OAuth implementation files"

FILES_TO_CHECK=(
  "Backend/toms_gym/routes/auth_routes.py"
  "Backend/toms_gym/db.py" 
  "my-frontend/src/auth/AuthContext.tsx"
  "my-frontend/src/pages/AuthCallback.tsx"
  "my-frontend/src/pages/AuthError.tsx"
  "my-frontend/src/components/GoogleLoginButton.tsx"
)

for file in "${FILES_TO_CHECK[@]}"; do
  if [ -f "$file" ]; then
    echo "✅ $file exists"
  else
    echo "❌ $file is missing"
    MISSING_FILES=true
  fi
done

if [ "$MISSING_FILES" = true ]; then
  echo -e "\n❌ Some required files are missing. OAuth implementation is incomplete."
  exit 1
fi

# Check file contents for key features
log_step "Checking for key OAuth features in the files"

# Backend auth_routes.py checks
if grep -q "init_oauth" Backend/toms_gym/routes/auth_routes.py && 
   grep -q "google/login" Backend/toms_gym/routes/auth_routes.py &&
   grep -q "callback" Backend/toms_gym/routes/auth_routes.py; then
  echo "✅ Backend auth_routes.py contains OAuth initialization and routes"
else
  echo "❌ Backend auth_routes.py is missing key OAuth functionality"
  MISSING_FEATURES=true
fi

# Frontend AuthContext.tsx checks
if grep -q "login" my-frontend/src/auth/AuthContext.tsx && 
   grep -q "handleOAuthCallback" my-frontend/src/auth/AuthContext.tsx &&
   grep -q "isAuthenticated" my-frontend/src/auth/AuthContext.tsx; then
  echo "✅ Frontend AuthContext.tsx contains OAuth authentication hooks"
else
  echo "❌ Frontend AuthContext.tsx is missing key OAuth functionality"
  MISSING_FEATURES=true
fi

# Frontend AuthCallback.tsx checks
if grep -q "useEffect" my-frontend/src/pages/AuthCallback.tsx && 
   grep -q "handleOAuthCallback" my-frontend/src/pages/AuthCallback.tsx; then
  echo "✅ Frontend AuthCallback.tsx contains OAuth callback handling"
else
  echo "❌ Frontend AuthCallback.tsx is missing key OAuth functionality"
  MISSING_FEATURES=true
fi

if [ "$MISSING_FEATURES" = true ]; then
  echo -e "\n❌ Some required OAuth features are missing. OAuth implementation is incomplete."
  exit 1
fi

echo -e "\n✅ OAuth implementation checks passed!"
echo "To run the full OAuth tests with a running backend, use: ./tests/run-oauth-tests.sh"
exit 0 