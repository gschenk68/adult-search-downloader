#!/bin/bash
# Quick deployment script for adult-search-downloader fix
# Run this on ss4 to pull the latest fix and rebuild the container

set -e

echo "=== Adult Search Downloader - Deploy Fix ==="
echo ""

# Navigate to build context
cd ~/docker/compose/schenkserver4/build-contexts/adult-search-downloader/

echo "📥 Pulling latest changes from GitHub..."
git pull origin master
echo ""

# Navigate to docker directory
cd ~/docker

echo "🔨 Rebuilding container..."
sudo docker compose -f docker-compose-schenkserver4.yml up adult-search-downloader --build -d
echo ""

echo "⏳ Waiting for container to start..."
sleep 5
echo ""

echo "✅ Deployment complete!"
echo ""
echo "📋 Container status:"
sudo docker ps | grep adult-search
echo ""

echo "📊 Recent logs:"
sudo docker logs adult-search-downloader --tail 10
echo ""

echo "🌐 Service available at: https://adult-search.gjsandstar.com"
echo ""
echo "🧪 Test the fix:"
echo "   1. Open https://adult-search.gjsandstar.com"
echo "   2. Search for any term"
echo "   3. Click Download on a result"
echo "   4. Should complete without directory errors"
