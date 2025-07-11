#!/bin/bash

# AWS EC2 FastAPI Deployment Fix Script
# This script fixes the environment loading and dependency issues

echo "🔧 AWS FastAPI Deployment Fix"
echo "============================="

# Get deployment info
source deployment_info.txt

echo "📋 Current Infrastructure:"
echo "   VPC: $VPC_ID"
echo "   EC2: $INSTANCE_ID ($PUBLIC_IP)"
echo "   RDS: $RDS_ENDPOINT"
echo "   ALB: $ALB_DNS"

echo ""
echo "🔧 Step 1: Installing missing dependencies on EC2..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "📦 Installing python-decouple (critical missing dependency)..."
pip3 install python-decouple

echo "📦 Installing other missing dependencies..."
pip3 install structlog==24.4.0  # Use compatible version
pip3 install python-jose[cryptography]

echo "✅ Dependencies installed"
EOF

echo ""
echo "🔧 Step 2: Creating proper production environment file..."

# Create a complete production environment file
cat > .env.production.aws << EOF
# =============================================================================
# AWS Production Environment Configuration
# Generated: $(date)
# =============================================================================

# Environment
ENVIRONMENT=production
DEBUG=false

# Security - Production Keys
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

# Database Configuration - AWS RDS PostgreSQL
DATABASE_URL=postgresql://dbadmin:${DB_PASSWORD}@${RDS_ENDPOINT}:5432/balance_tracker
DATABASE_TYPE=postgresql
DATABASE_SSL_MODE=require

# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=Balance Tracking System
VERSION=1.0.0

# CORS - Update with your actual domain
CORS_ORIGINS=http://${ALB_DNS},https://${ALB_DNS}
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting - Production settings
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST=5

# Password Requirements (Production)
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SPECIAL=true

# Email Configuration (Disabled for now)
EMAIL_ENABLED=false

# Security Headers
SECURITY_HEADERS_ENABLED=true
HTTPS_ONLY=false

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Health Check
HEALTH_CHECK_ENABLED=true
EOF

echo "✅ Created production environment file"

echo ""
echo "🔧 Step 3: Uploading corrected environment to EC2..."

# Upload the production environment file
scp -i trading-api-keypair.pem -o StrictHostKeyChecking=no \
    .env.production.aws \
    ec2-user@${PUBLIC_IP}:/tmp/

echo ""
echo "🔧 Step 4: Configuring and starting the application..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "📝 Installing production environment..."
sudo cp /tmp/.env.production.aws .env
sudo chown ec2-user:ec2-user .env

echo "📋 Verifying environment file..."
echo "Environment file contents (first 15 lines):"
head -15 .env

echo ""
echo "🧪 Testing configuration loading..."
python3 -c "
try:
    from decouple import config
    secret_key = config('SECRET_KEY', default='')
    environment = config('ENVIRONMENT', default='development')
    print(f'✅ Environment: {environment}')
    print(f'✅ SECRET_KEY length: {len(secret_key)} characters')
    if len(secret_key) >= 32:
        print('✅ SECRET_KEY is valid')
    else:
        print('❌ SECRET_KEY is too short')
        exit(1)
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
except Exception as e:
    print(f'❌ Configuration error: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ Configuration test passed"
else
    echo "❌ Configuration test failed"
    exit 1
fi

echo ""
echo "🚀 Starting FastAPI application..."

# Kill any existing processes
pkill -f uvicorn || echo "No existing processes to kill"

# Clear log file
sudo mkdir -p /var/log/trading-api
sudo chown ec2-user:ec2-user /var/log/trading-api
> /var/log/trading-api/app.log

# Start the application with explicit environment
export PYTHONPATH=/opt/trading-api:$PYTHONPATH
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info > /var/log/trading-api/app.log 2>&1 &

APP_PID=$!
echo "Started application with PID: $APP_PID"

# Wait for startup
echo "⏳ Waiting 25 seconds for application startup..."
sleep 25

# Check if process is still running
if ps -p $APP_PID > /dev/null 2>&1; then
    echo "✅ Application process is running (PID: $APP_PID)"
else
    echo "❌ Application process died"
    echo "Last 20 lines of log:"
    tail -20 /var/log/trading-api/app.log
    exit 1
fi

# Test the application
echo "🧪 Testing health endpoint..."
if curl -f -s http://localhost:8000/health > /dev/null; then
    echo "✅ Health endpoint is responding!"
    
    # Test the response content
    echo "Health response:"
    curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
else
    echo "❌ Health endpoint failed"
    echo "Application logs:"
    tail -30 /var/log/trading-api/app.log
    exit 1
fi

echo ""
echo "🧪 Testing root endpoint..."
if curl -f -s http://localhost:8000/ > /dev/null; then
    echo "✅ Root endpoint is responding!"
else
    echo "⚠️  Root endpoint failed (may be expected)"
fi

echo ""
echo "📊 Application Status:"
echo "   Process: Running (PID: $APP_PID)"
echo "   Health: ✅ Responding"
echo "   Logs: /var/log/trading-api/app.log"

EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ APPLICATION DEPLOYMENT SUCCESSFUL!"
    echo "======================================="
    echo ""
    echo "🌐 Access your application:"
    echo "   Direct EC2: http://${PUBLIC_IP}:8000/health"
    echo "   Load Balancer: http://${ALB_DNS}/health"
    echo ""
    echo "🔧 Management commands:"
    echo "   Check status: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'ps aux | grep uvicorn'"
    echo "   View logs: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'tail -f /var/log/trading-api/app.log'"
    echo "   Restart app: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'pkill -f uvicorn && cd /opt/trading-api && nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /var/log/trading-api/app.log 2>&1 &'"
    echo ""
    echo "📋 Infrastructure Summary:"
    echo "   VPC: $VPC_ID"
    echo "   EC2: $INSTANCE_ID"
    echo "   RDS: $RDS_ENDPOINT"
    echo "   ALB: $ALB_DNS"
    echo "   Environment: Production"
    echo ""
    echo "🧪 Test your API:"
    echo "   curl http://${PUBLIC_IP}:8000/health"
    echo "   curl http://${ALB_DNS}/health"
else
    echo ""
    echo "❌ DEPLOYMENT FAILED"
    echo "==================="
    echo ""
    echo "🔍 Troubleshooting steps:"
    echo "1. Check application logs:"
    echo "   ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'tail -50 /var/log/trading-api/app.log'"
    echo ""
    echo "2. Check if process is running:"
    echo "   ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'ps aux | grep uvicorn'"
    echo ""
    echo "3. Manual restart:"
    echo "   ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP}"
    echo "   cd /opt/trading-api"
    echo "   python3 -m uvicorn main:app --host 0.0.0.0 --port 8000"
fi

# Clean up temporary files
rm -f .env.production.aws

echo ""
echo "🔧 Deployment fix script completed"
