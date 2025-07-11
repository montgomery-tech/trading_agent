#!/bin/bash

# Fixed Dependency Installation - Resolving Redis Conflict
echo "🔧 Fixed Dependency Installation"
echo "================================"

# Get deployment info
source deployment_info.txt

echo "📋 Target EC2: $PUBLIC_IP"

echo ""
echo "🔧 Step 1: Installing dependencies with resolved conflicts..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "📦 Installing core dependencies (without Redis conflicts)..."

# Install core FastAPI and security dependencies first
pip3 install --user \
    fastapi==0.115.0 \
    uvicorn[standard]==0.32.0 \
    pydantic==2.8.0 \
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
    limits==3.6.0 \
    prometheus-client==0.19.0 \
    boto3==1.35.80 \
    botocore==1.35.80 \
    structlog==24.4.0

echo "✅ Core dependencies installed"

echo ""
echo "📦 Installing Redis with compatible versions..."

# Install Redis with compatible version for redis-py-cluster
pip3 install --user "redis>=3.0.0,<4.0.0"

echo "✅ Redis dependencies installed"

echo ""
echo "📦 Installing email validation..."
pip3 install --user "pydantic[email]==2.8.0"

echo "✅ Email validation installed"

echo ""
echo "🧪 Testing critical imports..."
python3 -c "
import sys
errors = []

# Test core imports
imports_to_test = [
    ('fastapi', 'fastapi'),
    ('bleach', 'bleach'),
    ('decouple', 'python-decouple'),
    ('uvicorn', 'uvicorn'),
    ('passlib.context', 'passlib'),
    ('validators', 'validators'),
    ('redis', 'redis'),
    ('structlog', 'structlog'),
    ('sqlalchemy', 'sqlalchemy'),
    ('jose', 'python-jose'),
]

for module, package in imports_to_test:
    try:
        __import__(module)
        print(f'✅ {package} imported successfully')
    except ImportError as e:
        errors.append(f'{package}: {e}')

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
echo "🔧 Step 2: Testing application imports..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "🧪 Testing application configuration and imports..."
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

# Test specific imports that were failing
try:
    print('Testing security imports...')
    import bleach
    print('✅ bleach imported')
    
    import validators
    print('✅ validators imported')
    
    from api.security.input_validation import validation_service
    print('✅ Input validation service imported successfully')
    
    from api.config import settings
    print('✅ Settings imported successfully')
    
    from api.jwt_service import jwt_service, password_service
    print('✅ JWT and password services imported successfully')
    
    # Test main application import
    print('Testing main application import...')
    import main
    print('✅ Main application module imported successfully')
    
except Exception as e:
    print(f'❌ Application import error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

print('✅ All application components imported successfully')
"

if [ $? -eq 0 ]; then
    echo "✅ Application import test passed"
else
    echo "❌ Application import test failed"
    exit 1
fi

EOF

if [ $? -eq 0 ]; then
    echo "✅ Application imports working"
else
    echo "❌ Application imports failed"
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

# Start with more detailed logging to catch any remaining issues
nohup python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    --access-log \
    > /var/log/trading-api/app.log 2>&1 &

APP_PID=$!
echo "Started application with PID: $APP_PID"

echo "⏳ Waiting 30 seconds for application startup..."
sleep 30

# Check if process is still running
if ps -p $APP_PID > /dev/null 2>&1; then
    echo "✅ Application process is running (PID: $APP_PID)"
    
    # Test health endpoint with multiple attempts
    echo "🧪 Testing health endpoint (with retries)..."
    
    HEALTH_SUCCESS=false
    for i in {1..6}; do
        echo "   Attempt $i/6..."
        if curl -f -s --connect-timeout 5 http://localhost:8000/health > /dev/null; then
            HEALTH_SUCCESS=true
            break
        fi
        sleep 5
    done
    
    if [ "$HEALTH_SUCCESS" = true ]; then
        echo "✅ Health endpoint is responding!"
        
        # Show the actual health response
        echo "📊 Health response:"
        curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
        
        echo ""
        echo "🧪 Testing other endpoints..."
        
        # Test root endpoint
        if curl -f -s --connect-timeout 5 http://localhost:8000/ > /dev/null; then
            echo "✅ Root endpoint responding"
        else
            echo "ℹ️  Root endpoint not responding (may be expected)"
        fi
        
        echo ""
        echo "✅ APPLICATION IS RUNNING SUCCESSFULLY!"
        echo "   Internal health: http://localhost:8000/health ✅"
        echo "   Process ID: $APP_PID"
        
    else
        echo "❌ Health endpoint is not responding after multiple attempts"
        echo "📄 Recent application logs:"
        tail -30 /var/log/trading-api/app.log
        exit 1
    fi
    
else
    echo "❌ Application process died during startup"
    echo "📄 Application logs:"
    tail -40 /var/log/trading-api/app.log
    exit 1
fi

EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 SUCCESS! FastAPI Application is Running!"
    echo "========================================="
    echo ""
    echo "🌐 Test your application now:"
    echo ""
    echo "1. Direct EC2 health check:"
    echo "   curl http://${PUBLIC_IP}:8000/health"
    echo ""
    echo "2. Load Balancer health check (may take 2-3 minutes):"
    echo "   curl http://${ALB_DNS}/health"
    echo ""
    echo "3. Check ALB target health:"
    echo "   aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN"
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
    echo "   Environment: Production"
    
else
    echo ""
    echo "❌ APPLICATION STARTUP FAILED"
    echo "============================="
    echo ""
    echo "🔍 Troubleshooting:"
    echo "1. Check detailed logs:"
    echo "   ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'tail -50 /var/log/trading-api/app.log'"
    echo ""
    echo "2. Try manual startup with debug output:"
    echo "   ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP}"
    echo "   cd /opt/trading-api"
    echo "   python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug"
fi

# Test external connectivity immediately
echo ""
echo "🧪 Testing external connectivity..."

if curl -f -s --connect-timeout 10 http://${PUBLIC_IP}:8000/health > /dev/null; then
    echo "✅ External health check successful!"
    echo ""
    echo "Response:"
    curl -s http://${PUBLIC_IP}:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://${PUBLIC_IP}:8000/health
else
    echo "❌ External health check failed"
    echo "   This may be due to security group rules or the application not being ready yet"
    echo "   Try again in a few minutes or check security group port 8000 rules"
fi

echo ""
echo "🔧 Fixed dependency installation completed"
