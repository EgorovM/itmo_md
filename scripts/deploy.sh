#!/bin/bash
# Deployment script for BankShield project

set -e

# Configuration
SERVER_HOST="${SERVER_HOST:-158.160.186.46}"
SERVER_USER="${SERVER_USER:-root}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/bankshield}"

echo "🚀 Deploying BankShield to $SERVER_USER@$SERVER_HOST:$DEPLOY_PATH"

# Check if SSH key exists
if [ ! -f ~/.ssh/id_rsa_deploy ]; then
    echo "❌ SSH key not found at ~/.ssh/id_rsa_deploy"
    echo "Please generate it first: ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_deploy -N ''"
    exit 1
fi

# Create deployment directory on server
echo "📁 Creating deployment directory..."
ssh -i ~/.ssh/id_rsa_deploy $SERVER_USER@$SERVER_HOST "mkdir -p $DEPLOY_PATH"

# Copy files to server
echo "📦 Copying files to server..."
rsync -avz --delete \
    -e "ssh -i ~/.ssh/id_rsa_deploy" \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    --exclude 'htmlcov' \
    --exclude '.venv' \
    --exclude 'data' \
    --exclude 'airflow/logs' \
    --exclude '.github' \
    ./ $SERVER_USER@$SERVER_HOST:$DEPLOY_PATH/

# Deploy on server
echo "🐳 Deploying Docker containers..."
ssh -i ~/.ssh/id_rsa_deploy $SERVER_USER@$SERVER_HOST << ENDSSH
    set -e
    cd $DEPLOY_PATH

    echo "Stopping existing containers..."
    docker compose down || true

    echo "Pulling latest images..."
    docker compose pull || true

    echo "Building and starting services..."
    docker compose up -d --build

    echo "Waiting for services to start..."
    sleep 30

    echo "Service status:"
    docker compose ps

    echo "Recent logs:"
    docker compose logs --tail=50
ENDSSH

echo "✅ Deployment completed!"
echo ""
echo "📊 Services:"
echo "   - Airflow: http://$SERVER_HOST:8080 (airflow/airflow)"
echo "   - Grafana: http://$SERVER_HOST:3001 (admin/admin)"
echo "   - PostgreSQL: $SERVER_HOST:5433"
echo "   - MongoDB: $SERVER_HOST:27017"
