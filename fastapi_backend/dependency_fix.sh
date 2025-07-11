#!/bin/bash

# Final Dependency Fix for AWS FastAPI Deployment
echo "🔧 Final Dependency Fix"
echo "======================="

# Get deployment info
source deployment_info.txt

echo "📋 Target EC2: $PUBLIC_IP"

echo ""
echo "🔧 Step 1: Installing all missing dependencies..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "📦 Installing complete requirements.txt dependencies..."

# Install all requirements with compatible versions
pip3 install --user \
    fastapi==0.115.0 \
    uvicorn[standard]==0.32.0 \
    pydantic==2.8.0 \
    pydantic[email]==2.8.0 \
    python-multipart==0.0.16 \
    python-decouple==3.8 \
    python-jose[cryptography]==3.3.0 \
    passlib[bcrypt]==1.7.4 \
    sqlalchemy==2.0.36 \
    psycopg2-binary==2.9.10 \
    alembic==1.14.0 \
    httpx==0.28.1 \
    validators==0.33.0 \
    bleach==6.2.0 \
    slowapi==0.1.9 \
    redis==5.0.1 \
    redis-py-cluster==2.1.3 \
    limits==3.6.0 \
    prometheus-client==0.19.0 \
    boto3==1.35.80 \
    botocore==1.35.80 \
    structlog==24.4.0

echo "✅ Dependencies installation completed"

echo ""
echo "🧪 Testing critical imports..."
python3 -c "
import sys
errors = []
try:
    import fastapi
    print('✅ fastapi imported successfully')
except ImportError as e:
    errors.append(f'fastapi: {e}')

try:
    import bleach
    print('✅ bleach imported successfully')
except ImportError as e:
    errors.append(f'bleach: {e}')

try:
    from decouple import config
    print('✅ python-decouple imported successfully')
except ImportError as e:
    errors.append(f'python-decouple: {e}')

try:
    import uvicorn
    print('✅ uvicorn imported successfully')
except ImportError as e:
    errors.append(f'uvicorn: {e}')

try:
    from passlib.context import CryptContext
    print('✅ passlib imported successfully')
except ImportError as e:
    errors.append(f'passlib: {e}')

try:
    import validators
    print('✅ validators imported successfully')
except ImportError as e:
    errors.append(f'validators: {e}')

if errors:
    print(f'❌ Import errors found:')
    for error in errors:
        print(f'   {error}')
    sys.exit(1)
else:
    print('✅ All critical dependencies imported successfully')
"

if [ $? -eq 0 ]; then
    echo "✅ Dependency test passed"
else
    echo "❌ Dependency test failed"
    exit 1
fi

EOF

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Dependency installation failed"
    exit 1
fi

echo ""
echo "🔧 Step 2: Testing configuration loading..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "🧪 Testing application imports and configuration..."
python3 -c "
import os
import sys

# Test environment loading
try:
    from decouple import config
    environment = config('ENVIRONMENT', default='development')
    secret_key = config('SECRET_KEY', default='')
    
    print(f'✅ Environment: {environment}')
    print(f'✅ SECRET_KEY length: {len(secret_key)} characters')
    
    if len(secret_key) >= 32:
        print('✅ SECRET_KEY is valid')
    else:
        print('❌ SECRET_KEY too short')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ Configuration error: {e}')
    sys.exit(1)

# Test critical application imports
try:
    # Test the specific import that was failing
    from api.security.input_validation import validation_service
    print('✅ Input validation service imported successfully')
    
    # Test other critical imports
    from api.config import settings
    print('✅ Settings imported successfully')
    
    from api.jwt_service import jwt_service, password_service
    print('✅ JWT and password services imported successfully')
    
except Exception as e:
    print(f'❌ Application import error: {e}')
    sys.exit(1)

print('✅ All application components imported successfully')
"

if [ $? -eq 0 ]; then
    echo "✅ Configuration and import test passed"
else
    echo "❌ Configuration or import test failed"
    exit 1
fi

EOF

if [ $? -eq 0 ]; then
    echo "✅ Configuration test passed"
else
    echo "❌ Configuration test failed"
    exit 1
fi

echo ""
echo "🚀 Step 3: Starting the FastAPI application..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "🔄 Cleaning up any existing processes..."
pkill -f uvicorn || echo "No existing processes to kill"

echo "📂 Ensuring log directory exists..."
sudo mkdir -p /var/log/trading-api
sudo chown ec2-user:ec2-user /var/log/trading-api

echo "🗑️  Clearing old logs..."
> /var/log/trading-api/app.log

echo "🚀 Starting FastAPI application..."
export PYTHONPATH=/opt/trading-api:$PYTHONPATH
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info > /var/log/trading-api/app.log 2>&1 &

APP_PID=$!
echo "Started application with PID: $APP_PID"

echo "⏳ Waiting 30 seconds for application startup..."
sleep 30

# Check if process is still running
if ps -p $APP_PID > /dev/null 2>&1; then
    echo "✅ Application process is running (PID: $APP_PID)"
    
    # Test health endpoint
    echo "🧪 Testing health endpoint..."
    sleep 5  # Extra wait for binding
    
    if curl -f -s --connect-timeout 10 http://localhost:8000/health > /dev/null; then
        echo "✅ Health endpoint is responding!"
        
        # Show the actual health response
        echo "📊 Health response:"
        curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
        
        echo ""
        echo "✅ APPLICATION IS RUNNING SUCCESSFULLY!"
        echo "   Internal health: http://localhost:8000/health ✅"
        echo "   Process ID: $APP_PID"
        
    else
        echo "❌ Health endpoint is not responding"
        echo "📄 Application logs:"
        tail -20 /var/log/trading-api/app.log
        exit 1
    fi
    
else
    echo "❌ Application process died during startup"
    echo "📄 Application logs:"
    tail -30 /var/log/trading-api/app.log
    exit 1
fi

EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 SUCCESS! FastAPI Application is Running!"
    echo "========================================="
    echo ""
    echo "🌐 Test your application:"
    echo "   Direct EC2: curl http://${PUBLIC_IP}:8000/health"
    echo "   Load Balancer: curl http://${ALB_DNS}/health"
    echo ""
    echo "🔧 Management commands:"
    echo "   View logs: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'tail -f /var/log/trading-api/app.log'"
    echo "   Check status: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'ps aux | grep uvicorn'"
    echo "   Restart: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'pkill -f uvicorn && cd /opt/trading-api && nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /var/log/trading-api/app.log 2>&1 &'"
    echo ""
    echo "📊 Infrastructure Summary:"
    echo "   VPC: $VPC_ID"
    echo "   EC2: $INSTANCE_ID ($PUBLIC_IP)"
    echo "   RDS: $RDS_ENDPOINT"
    echo "   ALB: $ALB_DNS"
    echo ""
    echo "🧪 Next Steps:"
    echo "1. Test the external health endpoint:"
    echo "   curl http://${PUBLIC_IP}:8000/health"
    echo ""
    echo "2. Wait for ALB health checks to pass (may take 2-3 minutes):"
    echo "   curl http://${ALB_DNS}/health"
    echo ""
    echo "3. Check target group health:"
    echo "   aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN"
    
else
    echo ""
    echo "❌ DEPLOYMENT STILL FAILED"
    echo "=========================="
    echo ""
    echo "🔍 Next troubleshooting steps:"
    echo "1. SSH into the server and check logs manually:"
    echo "   ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP}"
    echo "   cd /opt/trading-api"
    echo "   tail -50 /var/log/trading-api/app.log"
    echo ""
    echo "2. Try starting manually to see real-time errors:"
    echo "   python3 -m uvicorn main:app --host 0.0.0.0 --port 8000"
fi

echo ""
echo "🔧 Final dependency fix script completed"
