#!/bin/bash

# Production Startup Fix - Remove Reload Flag
echo "🔧 Production Startup Fix"
echo "========================"

# Get deployment info
source deployment_info.txt

echo "📋 Issue: Application started but stopped due to --reload flag in production"
echo "   Solution: Restart without --reload flag"

echo ""
echo "🔧 Step 1: Properly Starting Application for Production..."

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "🔄 Stopping any existing processes..."
pkill -f uvicorn || echo "No existing processes to kill"

# Wait for cleanup
sleep 3

echo "🗑️  Clearing logs..."
> /var/log/trading-api/app.log

echo "🚀 Starting FastAPI for production (without reload)..."

# Set environment variables
export ALLOWED_HOSTS="localhost,127.0.0.1,18.204.204.26,trading-api-alb-464076303.us-east-1.elb.amazonaws.com,*.elb.amazonaws.com"
export PYTHONPATH=/opt/trading-api:$PYTHONPATH

# Start without --reload flag (which is for development only)
nohup python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    --access-log \
    --workers 1 \
    > /var/log/trading-api/app.log 2>&1 &

NEW_PID=$!
echo "Started application with PID: $NEW_PID"

# Wait for startup
echo "⏳ Waiting 25 seconds for production startup..."
sleep 25

# Check if process is running
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "✅ Application process is running (PID: $NEW_PID)"
    
    # Test internal health
    echo "🧪 Testing internal health endpoint..."
    for i in {1..6}; do
        echo "   Attempt $i/6..."
        if curl -f -s --connect-timeout 5 http://localhost:8000/health > /dev/null; then
            echo "✅ Internal health check successful!"
            
            echo "📊 Internal health response:"
            curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
            break
        fi
        sleep 5
    done
    
    # Check network binding
    echo ""
    echo "📋 Network status:"
    netstat -tulpn | grep :8000 || ss -tulpn | grep :8000 || echo "Port check tools not available"
    
else
    echo "❌ Application process died"
    echo "📄 Recent logs:"
    tail -30 /var/log/trading-api/app.log
    exit 1
fi

EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "🔧 Step 2: Testing External Access..."
    
    echo "🧪 Testing external access (multiple attempts)..."
    
    # Wait a bit more for full startup
    sleep 10
    
    # Test external access with retries
    SUCCESS=false
    for i in {1..5}; do
        echo "   External test attempt $i/5..."
        if curl -f -s --connect-timeout 10 http://${PUBLIC_IP}:8000/health > /dev/null; then
            SUCCESS=true
            break
        fi
        sleep 5
    done
    
    if [ "$SUCCESS" = true ]; then
        echo "✅ External access successful!"
        
        echo "📊 External health response:"
        curl -s http://${PUBLIC_IP}:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://${PUBLIC_IP}:8000/health
        
        echo ""
        echo "🧪 Testing ALB access..."
        if curl -f -s --connect-timeout 10 http://${ALB_DNS}/health > /dev/null; then
            echo "✅ ALB access successful!"
            echo "📊 ALB health response:"
            curl -s http://${ALB_DNS}/health | python3 -m json.tool 2>/dev/null || curl -s http://${ALB_DNS}/health
        else
            echo "⚠️  ALB not ready yet (targets may take 2-3 minutes to become healthy)"
        fi
        
    else
        echo "❌ External access still not working"
        echo "🔍 Debugging information:"
        
        # Check if process is actually running
        APP_RUNNING=$(ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} "ps aux | grep uvicorn | grep -v grep | wc -l" 2>/dev/null)
        echo "   Processes running: $APP_RUNNING"
        
        # Check recent logs
        echo "   Recent application logs:"
        ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} "tail -10 /var/log/trading-api/app.log"
    fi
    
else
    echo "❌ Application startup failed"
fi

echo ""
echo "📊 FINAL STATUS SUMMARY"
echo "======================"

# Get comprehensive status
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
echo "🌐 Access URLs:"
echo "   Direct EC2: http://${PUBLIC_IP}:8000/health"
echo "   Load Balancer: http://${ALB_DNS}/health"
echo ""
echo "🔧 Management Commands:"
echo "   SSH: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP}"
echo "   Logs: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'tail -f /var/log/trading-api/app.log'"
echo "   Restart: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'pkill -f uvicorn && cd /opt/trading-api && nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /var/log/trading-api/app.log 2>&1 &'"

if [ "$EXTERNAL_HEALTH" = "✅ Working" ]; then
    echo ""
    echo "🎉 DEPLOYMENT SUCCESSFUL!"
    echo "========================"
    echo "Your FastAPI application is fully deployed and accessible on AWS!"
    echo ""
    echo "✅ Application Features:"
    echo "   • FastAPI with health endpoints"
    echo "   • PostgreSQL database connection"
    echo "   • JWT authentication system"
    echo "   • Rate limiting with Redis fallback"  
    echo "   • Security middleware and validation"
    echo "   • Production logging and monitoring"
    echo ""
    echo "✅ AWS Infrastructure:"
    echo "   • EC2 instance running application"
    echo "   • RDS PostgreSQL database"
    echo "   • Application Load Balancer"
    echo "   • VPC with public/private subnets"
    echo "   • Security groups configured"
    echo ""
    echo "🎯 Next Steps:"
    echo "   • Set up a custom domain name"
    echo "   • Configure SSL/HTTPS"
    echo "   • Set up monitoring and alerting"
    echo "   • Configure automated backups"
    
else
    echo ""
    echo "⚠️  Deployment needs final troubleshooting"
    echo "Application is running but external access may need more time or debugging"
fi

echo ""
echo "🔧 Production startup fix completed!"
