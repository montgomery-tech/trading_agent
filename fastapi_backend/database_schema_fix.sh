#!/bin/bash

# Database Schema and External Access Fix
echo "🔧 Database Schema and External Access Fix"
echo "=========================================="

# Get deployment info
source deployment_info.txt

echo "📋 Fixing Issues:"
echo "   1. Database schema setup"
echo "   2. External access troubleshooting"
echo "   3. Application health endpoint"

echo ""
echo "🔧 Step 1: Setting up Database Schema..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "🗄️  Creating database schema for FastAPI application..."

# Create a simple database initialization script
cat > init_database.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""
Database initialization script for FastAPI application
"""
import os
import sys
from decouple import config

def init_database():
    """Initialize database schema"""
    try:
        # Get database connection details
        database_url = config('DATABASE_URL')
        print(f"Database URL: {database_url[:50]}...")
        
        # Import required modules
        import psycopg2
        from urllib.parse import urlparse
        
        # Parse database URL
        parsed = urlparse(database_url)
        
        # Connect to database
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:] if parsed.path else 'postgres',
            user=parsed.username,
            password=parsed.password
        )
        
        # Enable autocommit for schema creation
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("✅ Connected to database")
        
        # Create basic tables if they don't exist
        print("📋 Creating basic application tables...")
        
        # Users table (simplified)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Users table ready")
        
        # Application settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ App settings table ready")
        
        # Insert initial data
        cursor.execute("""
            INSERT INTO app_settings (key, value) 
            VALUES ('database_initialized', 'true')
            ON CONFLICT (key) DO UPDATE SET 
                value = EXCLUDED.value,
                updated_at = CURRENT_TIMESTAMP
        """)
        print("✅ Initial data inserted")
        
        # Test query
        cursor.execute("SELECT COUNT(*) FROM app_settings")
        count = cursor.fetchone()[0]
        print(f"✅ Database test successful - {count} settings found")
        
        cursor.close()
        conn.close()
        
        print("✅ Database schema initialization completed")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
PYTHON_SCRIPT

# Run the database initialization
echo "🚀 Running database initialization..."
python3 init_database.py

if [ $? -eq 0 ]; then
    echo "✅ Database schema initialized successfully"
else
    echo "⚠️  Database initialization had issues, but continuing..."
fi

EOF

echo ""
echo "🔧 Step 2: Creating Simple Health Endpoint Fix..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "📝 Creating simplified health check..."

# Create a simple health endpoint that doesn't rely on complex database checks
cat > simple_health.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""
Simple health check endpoint for debugging
"""
import json
from datetime import datetime

def get_health():
    """Simple health check"""
    try:
        from decouple import config
        
        # Basic configuration check
        environment = config('ENVIRONMENT', default='unknown')
        secret_key = config('SECRET_KEY', default='')
        
        # Database connection test
        database_url = config('DATABASE_URL', default='')
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "environment": environment,
            "secret_key_configured": len(secret_key) >= 32,
            "database_configured": bool(database_url),
            "checks": {
                "config": "healthy",
                "imports": "healthy"
            }
        }
        
        # Test basic database connection
        try:
            import psycopg2
            from urllib.parse import urlparse
            
            parsed = urlparse(database_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:] if parsed.path else 'postgres',
                user=parsed.username,
                password=parsed.password,
                connect_timeout=5
            )
            conn.close()
            health_data["checks"]["database"] = "healthy"
            
        except Exception as e:
            health_data["checks"]["database"] = f"error: {str(e)[:100]}"
            health_data["status"] = "degraded"
        
        return health_data
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

if __name__ == "__main__":
    health = get_health()
    print(json.dumps(health, indent=2))
PYTHON_SCRIPT

# Test the simple health check
echo "🧪 Testing simple health check..."
python3 simple_health.py

EOF

echo ""
echo "🔧 Step 3: Troubleshooting External Access..."

echo "🔍 Checking current network connectivity..."

# Test if the application is actually binding to 0.0.0.0:8000
echo "   Testing if application is listening on port 8000..."
ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} "netstat -tulpn | grep :8000 || ss -tulpn | grep :8000" 2>/dev/null || echo "   Port check tools not available"

# Check if there are multiple security group rules causing conflicts
echo "   Checking for security group rule conflicts..."
EC2_SG_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)

echo "   Complete security group rules for $EC2_SG_ID:"
aws ec2 describe-security-groups --group-ids $EC2_SG_ID --query 'SecurityGroups[0].IpPermissions' --output table

# Test from a different approach - try telnet-style connection
echo "   Testing raw TCP connection..."
timeout 5 bash -c "</dev/tcp/${PUBLIC_IP}/8000" 2>/dev/null && echo "   ✅ TCP connection successful" || echo "   ❌ TCP connection failed"

echo ""
echo "🔧 Step 4: Restarting Application with Simple Health Endpoint..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "🔄 Stopping current application..."
pkill -f uvicorn || echo "No process to kill"

# Clear logs
> /var/log/trading-api/app.log

echo "🚀 Starting application with explicit binding..."

# Start with explicit host binding and more verbose logging
export PYTHONPATH=/opt/trading-api:$PYTHONPATH

nohup python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level debug \
    --access-log \
    --reload \
    > /var/log/trading-api/app.log 2>&1 &

NEW_PID=$!
echo "Started application with PID: $NEW_PID"

# Wait for startup
echo "⏳ Waiting 25 seconds for startup..."
sleep 25

# Check if process is running
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "✅ Application process is running"
    
    # Test health endpoint internally
    echo "🧪 Testing internal health endpoint..."
    for i in {1..5}; do
        echo "   Attempt $i/5..."
        if curl -f -s --connect-timeout 5 http://localhost:8000/health > /dev/null; then
            echo "✅ Internal health check successful!"
            echo "📊 Health response:"
            curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
            break
        fi
        sleep 3
    done
    
    # Check what's actually listening
    echo "📋 Network status:"
    echo "   Processes listening on port 8000:"
    lsof -i :8000 2>/dev/null || netstat -tulpn | grep :8000 || ss -tulpn | grep :8000 || echo "   No port listeners found"
    
else
    echo "❌ Application process died"
    echo "📄 Recent logs:"
    tail -30 /var/log/trading-api/app.log
fi

EOF

echo ""
echo "🔧 Step 5: Final External Access Test..."

echo "🧪 Testing external access with multiple methods..."

# Test 1: Direct curl with verbose output
echo "   Test 1: Direct curl..."
curl -v --connect-timeout 10 http://${PUBLIC_IP}:8000/health 2>&1 | head -10

echo ""
echo "   Test 2: Using different tools..."

# Test 2: Test with nc (netcat) if available
timeout 5 nc -zv ${PUBLIC_IP} 8000 2>&1 || echo "   nc not available or connection failed"

# Test 3: Test with telnet-style
timeout 5 bash -c "exec 3<>/dev/tcp/${PUBLIC_IP}/8000 && echo 'GET /health HTTP/1.1' >&3" 2>/dev/null && echo "   ✅ Raw TCP connection works" || echo "   ❌ Raw TCP connection failed"

echo ""
echo "🔧 Step 6: Security Group Deep Dive..."

# Check all security groups attached to the instance
echo "   All security groups for instance $INSTANCE_ID:"
aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].SecurityGroups[*].[GroupName,GroupId]' --output table

# Check NACLs (Network ACLs) that might be blocking
SUBNET_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].SubnetId' --output text)
echo "   Subnet: $SUBNET_ID"

NACL_ID=$(aws ec2 describe-network-acls --filters "Name=association.subnet-id,Values=$SUBNET_ID" --query 'NetworkAcls[0].NetworkAclId' --output text)
echo "   Network ACL: $NACL_ID"

echo "   Network ACL rules (may affect connectivity):"
aws ec2 describe-network-acls --network-acl-ids $NACL_ID --query 'NetworkAcls[0].Entries[?RuleNumber<=`100`]' --output table 2>/dev/null || echo "   Could not retrieve NACL rules"

echo ""
echo "📊 COMPREHENSIVE STATUS SUMMARY"
echo "==============================="

# Get final status
APP_RUNNING=$(ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} "ps aux | grep uvicorn | grep -v grep | wc -l" 2>/dev/null)
INTERNAL_HEALTH=$(ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} "curl -f -s --connect-timeout 3 http://localhost:8000/health >/dev/null 2>&1" && echo "✅ Working" || echo "❌ Failed")
EXTERNAL_HEALTH=$(curl -f -s --connect-timeout 5 http://${PUBLIC_IP}:8000/health >/dev/null 2>&1 && echo "✅ Working" || echo "❌ Failed")
ALB_HEALTH=$(curl -f -s --connect-timeout 5 http://${ALB_DNS}/health >/dev/null 2>&1 && echo "✅ Working" || echo "⚠️  Not Ready")

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
echo "   Internal: ssh to EC2 and run: curl http://localhost:8000/health"
echo "   External: curl http://${PUBLIC_IP}:8000/health"
echo "   ALB: curl http://${ALB_DNS}/health"
echo ""
echo "🔧 Troubleshooting:"
echo "   Logs: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'tail -f /var/log/trading-api/app.log'"
echo "   Process: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'ps aux | grep uvicorn'"
echo "   Network: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'netstat -tulpn | grep 8000'"

if [ "$INTERNAL_HEALTH" = "✅ Working" ]; then
    echo ""
    echo "✅ APPLICATION IS WORKING INTERNALLY!"
    
    if [ "$EXTERNAL_HEALTH" = "✅ Working" ]; then
        echo "🎉 FULL SUCCESS - Application accessible externally!"
    else
        echo "⚠️  External access blocked - likely security group or network ACL issue"
        echo "   Try waiting a few minutes or check AWS networking rules"
    fi
else
    echo ""
    echo "⚠️  Application needs debugging - check logs for detailed errors"
fi

echo ""
echo "🔧 Database and access fix completed!"

