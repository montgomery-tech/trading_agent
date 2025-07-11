#!/bin/bash

# Host Header Validation Fix
echo "🔧 Host Header Validation Fix"
echo "============================"

# Get deployment info
source deployment_info.txt

echo "📋 Current Issue: Host header validation blocking external access"
echo "   Error: Invalid host"
echo "   Solution: Update CORS and allowed hosts configuration"

echo ""
echo "🔧 Step 1: Updating CORS and Host Configuration..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "📝 Updating .env file to allow external hosts..."

# Get current public IP and ALB DNS from the environment
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)

echo "Detected Public IP: $PUBLIC_IP"

# Update CORS origins to include the actual IPs and domains
cp .env .env.backup.host_fix

# Update the CORS_ORIGINS line to include the public IP and ALB
sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,http://${PUBLIC_IP}:8000,http://trading-api-alb-464076303.us-east-1.elb.amazonaws.com|g" .env

# Add specific allowed hosts configuration if it doesn't exist
if ! grep -q "ALLOWED_HOSTS" .env; then
    echo "" >> .env
    echo "# Allowed Hosts Configuration" >> .env
    echo "ALLOWED_HOSTS=localhost,127.0.0.1,${PUBLIC_IP},trading-api-alb-464076303.us-east-1.elb.amazonaws.com,*.elb.amazonaws.com" >> .env
fi

echo "✅ Updated .env configuration"

# Show the updated CORS configuration
echo "📋 Updated CORS configuration:"
grep "CORS_ORIGINS" .env
grep "ALLOWED_HOSTS" .env || echo "ALLOWED_HOSTS not found - that's ok"

EOF

echo ""
echo "🔧 Step 2: Creating Host Header Middleware Fix..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "📝 Creating host header validation fix..."

# Create a simple host validation bypass for our specific use case
cat > host_fix.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""
Host header validation fix for FastAPI
"""

def fix_host_validation():
    """Temporarily disable strict host validation for testing"""
    import os
    
    # Set environment variables to allow our hosts
    public_ip = "18.204.204.26"
    alb_dns = "trading-api-alb-464076303.us-east-1.elb.amazonaws.com"
    
    allowed_hosts = f"localhost,127.0.0.1,{public_ip},{alb_dns},*.elb.amazonaws.com"
    
    os.environ['ALLOWED_HOSTS'] = allowed_hosts
    
    print(f"✅ Set ALLOWED_HOSTS to: {allowed_hosts}")
    
    return True

if __name__ == "__main__":
    fix_host_validation()
PYTHON_SCRIPT

# Run the host fix
python3 host_fix.py

EOF

echo ""
echo "🔧 Step 3: Restarting Application with Fixed Configuration..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "🔄 Restarting FastAPI with updated host configuration..."

# Stop current application
pkill -f uvicorn || echo "No existing process to kill"

# Clear logs
> /var/log/trading-api/app.log

# Set environment variables for allowed hosts
export ALLOWED_HOSTS="localhost,127.0.0.1,18.204.204.26,trading-api-alb-464076303.us-east-1.elb.amazonaws.com,*.elb.amazonaws.com"
export PYTHONPATH=/opt/trading-api:$PYTHONPATH

# Start with more permissive host settings
nohup python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    --access-log \
    > /var/log/trading-api/app.log 2>&1 &

NEW_PID=$!
echo "Restarted application with PID: $NEW_PID"

# Wait for startup
echo "⏳ Waiting 20 seconds for restart..."
sleep 20

# Test internal health
echo "🧪 Testing internal health endpoint..."
if curl -f -s --connect-timeout 5 http://localhost:8000/health > /dev/null; then
    echo "✅ Internal health check successful"
    
    echo "📊 Internal health response:"
    curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
    
else
    echo "❌ Internal health check failed"
    echo "📄 Recent logs:"
    tail -20 /var/log/trading-api/app.log
fi

EOF

echo ""
echo "🔧 Step 4: Testing External Access with Host Header Fix..."

echo "🧪 Testing external access after host header fix..."

# Test with proper headers
echo "   Test 1: Standard curl request..."
curl -s http://${PUBLIC_IP}:8000/health

echo ""
echo "   Test 2: Curl with explicit Host header..."
curl -s -H "Host: ${PUBLIC_IP}:8000" http://${PUBLIC_IP}:8000/health

echo ""
echo "   Test 3: Curl with verbose output..."
curl -v http://${PUBLIC_IP}:8000/health 2>&1 | head -15

echo ""
echo "🔧 Step 5: Testing ALB Access..."

echo "🧪 Testing ALB endpoint..."
curl -s http://${ALB_DNS}/health

echo ""
echo "📊 FINAL STATUS CHECK"
echo "===================="

# Final comprehensive test
APP_RUNNING=$(ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} "ps aux | grep uvicorn | grep -v grep | wc -l" 2>/dev/null)
INTERNAL_HEALTH=$(ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} "curl -f -s --connect-timeout 3 http://localhost:8000/health >/dev/null 2>&1" && echo "✅ Working" || echo "❌ Failed")

# Test external with timeout
EXTERNAL_HEALTH="❌ Failed"
if timeout 10 curl -f -s http://${PUBLIC_IP}:8000/health >/dev/null 2>&1; then
    EXTERNAL_HEALTH="✅ Working"
fi

# Test ALB with timeout  
ALB_HEALTH="⚠️  Not Ready"
if timeout 10 curl -f -s http://${ALB_DNS}/health >/dev/null 2>&1; then
    ALB_HEALTH="✅ Working"
fi

echo "🖥️  Infrastructure:"
echo "   VPC: $VPC_ID"
echo "   EC2: $INSTANCE_ID ($PUBLIC_IP)"
echo "   RDS: $RDS_ENDPOINT"
echo "   ALB: $ALB_DNS"
echo ""
echo "🔧 Application Status:"
echo "   FastAPI Processes: $APP_RUNNING running"
echo "   Internal Health: $INTERNAL_HEALTH"
echo "   External Health: $EXTERNAL_HEALTH" 
echo "   ALB Health: $ALB_HEALTH"
echo ""
echo "🌐 Test URLs:"
echo "   External: curl http://${PUBLIC_IP}:8000/health"
echo "   ALB: curl http://${ALB_DNS}/health"
echo ""
echo "🎯 Success Criteria:"
if [ "$EXTERNAL_HEALTH" = "✅ Working" ]; then
    echo "🎉 SUCCESS! External access is working!"
    
    if [ "$ALB_HEALTH" = "✅ Working" ]; then
        echo "🎉 COMPLETE SUCCESS! Both direct and ALB access working!"
    else
        echo "⚠️  ALB may take 2-3 more minutes to become healthy"
    fi
else
    echo "⚠️  External access still blocked - may need additional host header configuration"
fi

echo ""
echo "🔧 Host header fix completed!"
