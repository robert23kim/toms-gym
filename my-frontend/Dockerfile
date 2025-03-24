FROM node:18-alpine AS build

# Set environment variables to force esbuild to use the correct binary
ENV ESBUILD_BINARY_PATH=/app/node_modules/esbuild/bin/esbuild
ENV ESBUILD_ARCH=amd64
ENV ESBUILD_PLATFORM=linux

WORKDIR /app

COPY package.json package-lock.json* ./

RUN npm install --force

COPY . .

RUN npm run build

# Serve the app using Nginx
FROM nginx:1.23-alpine

WORKDIR /usr/share/nginx/html

RUN rm -rf ./*

COPY --from=build /app/dist ./

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

