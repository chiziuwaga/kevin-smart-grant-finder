#!/bin/bash

echo "Building and deploying Smart Grant Finder frontend..."

# Ensure dependencies are installed
npm install

# Build the project
npm run build

# Install Vercel CLI if not already installed
if ! [ -x "$(command -v vercel)" ]; then
  echo "Installing Vercel CLI..."
  npm install -g vercel
fi

# Deploy to Vercel
echo "Deploying to Vercel..."
vercel --prod

echo "Deployment complete!" 