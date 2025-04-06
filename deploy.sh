#!/bin/bash

# Exit on any error
set -e

echo "🚀 Starting deployment pipeline..."

# Function to show spinner while waiting
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

echo "📦 Building and deploying backend..."
gcloud builds submit --tag gcr.io/toms-gym/my-python-backend Backend/ &
spinner $!
echo "✅ Backend build completed"

gcloud run deploy my-python-backend \
  --image gcr.io/toms-gym/my-python-backend \
  --platform managed \
  --region us-east1 \
  --allow-unauthenticated
echo "✅ Backend deployed successfully"

echo "📦 Building and deploying frontend..."
gcloud builds submit --config=cloudbuild.yaml --machine-type=e2-highcpu-32 &
spinner $!
echo "✅ Frontend build completed"

gcloud run deploy my-frontend \
  --image gcr.io/toms-gym/my-frontend \
  --platform managed \
  --region us-east1 \
  --allow-unauthenticated
echo "✅ Frontend deployed successfully"

echo "🎉 Deployment pipeline completed successfully!"

# Print the service URLs
echo "🌐 Service URLs:"
echo "Backend: $(gcloud run services describe my-python-backend --platform managed --region us-east1 --format 'value(status.url)')"
echo "Frontend: $(gcloud run services describe my-frontend --platform managed --region us-east1 --format 'value(status.url)')" 