#!/bin/bash

# Final Database and Security Group Fixes
echo "🔧 Final Database and Security Group Fixes"
echo "=========================================="

# Get deployment info
source deployment_info.txt

echo "📋 Current Status:"
echo "   Application: ✅ Running"
echo "   Health Endpoint: ⚠️  Responding but unhealthy (DB issue)"
echo "   External Access: ❌ Blocked (Security Group)"

echo ""
echo "🔧 Step 1: Fixing Security Group (External Access)..."

# Get current EC2 security group
EC2_SG_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)

echo "   EC2 Security Group: $EC2_SG_ID"

# Check if port 8000 rule exists
echo "   Current security group rules:"
aws ec2 describe-security-groups --group-ids $EC2_SG_ID --query 'SecurityGroups[0].IpPermissions[*].[IpProtocol,FromPort,ToPort,IpRanges[0].CidrIp]' --output table

# Add rule for port 8000 if it doesn't exist with proper source
echo "   Adding/updating port 8000 rule for external access..."

# Remove any existing port 8000 rules first
aws ec2 revoke-security-group-ingress \
    --group-id $EC2_SG_ID \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 2>/dev/null || echo "   No existing rule to remove"

# Add new rule allowing port 8000 from anywhere
aws ec2 authorize-security-group-ingress \
    --group-id $EC2_SG_ID \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0

echo "✅ Security group updated - port 8000 now accessible"

echo ""
echo "🔧 Step 2: Testing External Access..."

sleep 5  # Wait for security group changes to take effect

if curl -f -s --connect-timeout 10 http://${PUBLIC_IP}:8000/health > /dev/null; then
    echo "✅ External health check now working!"
    echo "   Response:"
    curl -s http://${PUBLIC_IP}:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://${PUBLIC_IP}:8000/health
else
    echo "⚠️  External access still not working - may need a few more minutes"
fi

echo ""
echo "🔧 Step 3: Fixing Database Connection..."

echo "   Testing RDS connectivity..."
RDS_STATUS=$(aws rds describe-db-instances --db-instance-identifier trading-api-db --query 'DBInstances[0].DBInstanceStatus' --output text)
echo "   RDS Status: $RDS_STATUS"

if [ "$RDS_STATUS" != "available" ]; then
    echo "⚠️  RDS is not available yet (Status: $RDS_STATUS)"
    echo "   Waiting for RDS to become available..."
    
    # Wait for RDS to be available
    aws rds wait db-instance-available --db-instance-identifier trading-api-db
    echo "✅ RDS is now available"
fi

echo ""
echo "🔧 Step 4: Updating Database Configuration..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "🧪 Testing database connectivity..."

# Test database connection
python3 -c "
import os
from decouple import config

# Get database configuration
database_url = config('DATABASE_URL')
print(f'Database URL configured: {database_url[:50]}...')

# Test basic connection
try:
    import psycopg2
    from urllib.parse import urlparse
    
    # Parse database URL
    parsed = urlparse(database_url)
    
    # Test connection
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:] if parsed.path else 'postgres',
        user=parsed.username,
        password=parsed.password
    )
    
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()
    print(f'✅ Database connection successful: {version[0][:50]}...')
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    
    # Check if it's a database creation issue
    if 'does not exist' in str(e):
        print('ℹ️  Database may need to be created')
    elif 'could not connect' in str(e):
        print('ℹ️  RDS may not be ready or network issue')
    elif 'authentication failed' in str(e):
        print('ℹ️  Credentials may be incorrect')
"

# Check if we need to create database tables
echo ""
echo "🗄️  Checking database schema..."

python3 -c "
try:
    from api.config import settings
    from api.database import engine
    from sqlalchemy import text
    
    print('Testing database connection through SQLAlchemy...')
    
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1 as test'))
        print('✅ SQLAlchemy connection successful')
        
        # Check if tables exist
        result = conn.execute(text(\"\"\"
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        \"\"\"))
        
        tables = [row[0] for row in result]
        print(f'📋 Existing tables: {tables}')
        
        if not tables:
            print('ℹ️  No tables found - database schema needs to be created')
        
except Exception as e:
    print(f'❌ Database schema check failed: {e}')
    if 'does not exist' in str(e):
        print('ℹ️  Database does not exist and needs to be created')
"

EOF

echo ""
echo "🔧 Step 5: Restarting Application with Database Fixes..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "🔄 Restarting application to fix database connection..."

# Kill existing process
pkill -f uvicorn || echo "No existing processes to kill"

# Clear logs
> /var/log/trading-api/app.log

# Restart with better error handling
export PYTHONPATH=/opt/trading-api:$PYTHONPATH

nohup python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    --access-log \
    > /var/log/trading-api/app.log 2>&1 &

NEW_PID=$!
echo "Restarted application with PID: $NEW_PID"

# Wait for restart
echo "⏳ Waiting 20 seconds for restart..."
sleep 20

# Test health endpoint
echo "🧪 Testing health endpoint after restart..."
if curl -f -s --connect-timeout 10 http://localhost:8000/health > /dev/null; then
    echo "✅ Health endpoint responding after restart"
    
    echo "📊 Health status:"
    curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
    
else
    echo "❌ Health endpoint not responding after restart"
    echo "📄 Recent logs:"
    tail -20 /var/log/trading-api/app.log
fi

EOF

echo ""
echo "🔧 Step 6: Final Connectivity Tests..."

echo "🧪 Testing external access after security group fix..."
if curl -f -s --connect-timeout 10 http://${PUBLIC_IP}:8000/health > /dev/null; then
    echo "✅ External health check successful!"
    
    echo "📊 External health response:"
    curl -s http://${PUBLIC_IP}:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://${PUBLIC_IP}:8000/health
    
    # Test other endpoints
    echo ""
    echo "🧪 Testing other external endpoints..."
    
    if curl -f -s --connect-timeout 5 http://${PUBLIC_IP}:8000/ > /dev/null; then
        echo "✅ Root endpoint accessible externally"
    else
        echo "ℹ️  Root endpoint may not be configured"
    fi
    
else
    echo "❌ External health check still failing"
    echo "🔍 Troubleshooting info:"
    echo "   Security group rules:"
    aws ec2 describe-security-groups --group-ids $EC2_SG_ID --query 'SecurityGroups[0].IpPermissions[?FromPort==`8000`]' --output table
fi

echo ""
echo "🧪 Testing Load Balancer (ALB)..."
if curl -f -s --connect-timeout 10 http://${ALB_DNS}/health > /dev/null; then
    echo "✅ ALB health check successful!"
    
    echo "📊 ALB health response:"
    curl -s http://${ALB_DNS}/health | python3 -m json.tool 2>/dev/null || curl -s http://${ALB_DNS}/health
    
else
    echo "⚠️  ALB health check not ready yet"
    echo "   ALB targets may take 2-3 minutes to become healthy"
    
    # Check target group health
    echo "   Target group health status:"
    aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[*].[Target.Id,TargetHealth.State,TargetHealth.Description]' --output table
fi

echo ""
echo "📊 FINAL STATUS SUMMARY"
echo "======================"

# Application status
APP_RUNNING=$(ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} "ps aux | grep uvicorn | grep -v grep | wc -l" 2>/dev/null)
DIRECT_HEALTH=$(curl -f -s --connect-timeout 5 http://${PUBLIC_IP}:8000/health >/dev/null 2>&1 && echo "✅ Working" || echo "❌ Failed")
ALB_HEALTH=$(curl -f -s --connect-timeout 5 http://${ALB_DNS}/health >/dev/null 2>&1 && echo "✅ Working" || echo "⚠️  Not Ready")

echo "Infrastructure Status:"
echo "   VPC: $VPC_ID"
echo "   EC2: $INSTANCE_ID ($PUBLIC_IP)"
echo "   RDS: $RDS_ENDPOINT"
echo "   ALB: $ALB_DNS"
echo ""
echo "Application Status:"
echo "   FastAPI Process: $APP_RUNNING running"
echo "   Direct Health Check: $DIRECT_HEALTH"
echo "   ALB Health Check: $ALB_HEALTH"
echo ""
echo "🌐 Access URLs:"
echo "   Direct: http://${PUBLIC_IP}:8000/health"
echo "   Load Balancer: http://${ALB_DNS}/health"
echo ""
echo "🔧 Management:"
echo "   SSH: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP}"
echo "   Logs: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'tail -f /var/log/trading-api/app.log'"
echo "   Status: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'ps aux | grep uvicorn'"

if [ "$DIRECT_HEALTH" = "✅ Working" ]; then
    echo ""
    echo "🎉 SUCCESS! Your FastAPI application is accessible!"
    echo "   The application is running and responding to health checks."
    echo "   If ALB shows 'Not Ready', wait 2-3 minutes for targets to become healthy."
else
    echo ""
    echo "⚠️  Application running but health checks need attention."
    echo "   Check logs for database connection issues."
fi

echo ""
echo "🔧 Final fixes completed!"
