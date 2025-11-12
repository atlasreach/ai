#!/bin/bash
# Start FastAPI Backend Server

echo "🚀 Starting AI Character Generation API..."
echo ""

# Load environment variables
export $(cat .env | xargs)

# Start server
python3 -m backend.main
