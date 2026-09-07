#!/bin/bash
# Deployment script for adult-search-downloader

set -e

echo "🚀 Deploying Adult Search Downloader v2.0"
echo "=========================================="

# Configuration
REMOTE_HOST="gschenk68@192.168.10.162"
REMOTE_DIR="/home/gschenk68/docker"
APP_NAME="adult-search-downloader"

# Check if we're deploying standalone or VPN mode
MODE="${1:-standalone}"

echo ""
echo "📋 Deployment Mode: $MODE"
echo ""

# Build Docker image locally first (optional - can build on server)
echo "🔨 Building Docker image..."
docker build -t $APP_NAME:latest . || echo "Local build skipped (will build on server)"

# Deploy files to server
echo "📦 Copying files to ss4..."
ssh $REMOTE_HOST "mkdir -p $REMOTE_DIR/$APP_NAME"

scp searcher.py Dockerfile $REMOTE_HOST:$REMOTE_DIR/$APP_NAME/

if [ "$MODE" = "vpn" ]; then
    echo "🔒 Using VPN mode (qbt-vpn network)"
    scp docker-compose.yml $REMOTE_HOST:$REMOTE_DIR/$APP_NAME/
else
    echo "🌐 Using standalone mode (direct internet)"
    scp docker-compose-standalone.yml $REMOTE_HOST:$REMOTE_DIR/$APP_NAME/docker-compose.yml
fi

# Deploy to server
echo "🚢 Deploying on ss4..."
ssh $REMOTE_HOST "cd $REMOTE_DIR/$APP_NAME && docker compose down 2>/dev/null || true"
ssh $REMOTE_HOST "cd $REMOTE_DIR/$APP_NAME && docker compose build"
ssh $REMOTE_HOST "cd $REMOTE_DIR/$APP_NAME && docker compose up -d"

# Wait for startup
echo "⏳ Waiting for service to start..."
sleep 5

# Check status
echo "✅ Checking status..."
ssh $REMOTE_HOST "docker ps | grep $APP_NAME"

echo ""
echo "=========================================="
echo "✨ Deployment Complete!"
echo ""

if [ "$MODE" = "vpn" ]; then
    echo "🔗 Access via qbt-vpn network at port 5000"
    echo "   (Internal access through VPN container)"
else
    echo "🔗 Access at: http://192.168.10.162:5556"
fi

echo ""
echo "📊 View logs:"
echo "   ssh $REMOTE_HOST 'docker logs -f $APP_NAME'"
echo ""
echo "🛑 Stop service:"
echo "   ssh $REMOTE_HOST 'cd $REMOTE_DIR/$APP_NAME && docker compose down'"
echo ""
