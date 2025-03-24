# Use a minimal Node.js base image
FROM node:18-alpine AS build

# Set working directory
WORKDIR /app

# Set environment variables to optimize esbuild
ENV ESBUILD_BINARY_PATH=/app/node_modules/esbuild/bin/esbuild
ENV ESBUILD_ARCH=amd64
ENV ESBUILD_PLATFORM=linux

# Copy only package.json and package-lock.json first to leverage caching
COPY package.json package-lock.json* ./

# Install dependencies efficiently
RUN npm ci --no-audit --prefer-offline

# Copy the rest of the application code
COPY . .

# Build the React app
RUN npm run build

# Use a lightweight Nginx image for serving static files
FROM nginx:1.23-alpine

# Set working directory inside Nginx
WORKDIR /usr/share/nginx/html

# Remove default Nginx static files
RUN rm -rf ./*

# Copy built frontend files from the previous stage
COPY --from=build /app/dist ./

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]

