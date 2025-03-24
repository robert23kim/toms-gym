# Use a minimal Node.js base image
FROM node:18-alpine AS build

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json first for caching
COPY package.json package-lock.json ./

# Install dependencies efficiently
RUN npm ci --no-audit --prefer-offline

# Copy the rest of the application files
COPY . .

# Build the React app
RUN npm run build

# Use lightweight Nginx image for serving static files
FROM nginx:1.23-alpine

# Set working directory inside Nginx
WORKDIR /usr/share/nginx/html

# Remove default Nginx static files
RUN rm -rf ./*

# Copy built frontend files from the previous stage
COPY --from=build /app/dist ./

# Copy the custom Nginx template for dynamic port configuration
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Start Nginx (port is dynamically set by Cloud Run via PORT env variable)
CMD ["nginx", "-g", "daemon off;"]

