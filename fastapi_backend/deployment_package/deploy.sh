#!/bin/bash
# Application deployment script (runs on EC2)

set -e

echo "🚀 Deploying Trading API..."

# Install Python dependencies
pip3 install -r requirements.txt

# Create log directory
sudo mkdir -p /var/log/trading-api
sudo chown ec2-user:ec2-user /var/log/trading-api

# Set up database (if schema file exists)
if [ -f "setup_database.py" ]; then
    echo "Setting up database schema..."
    python3 setup_database.py postgresql
fi

# Start application with PM2
pm2 start ecosystem.config.js --env production
pm2 save
pm2 startup

echo "✅ Deployment completed!"
echo "🌐 API should be available at the load balancer endpoint"
