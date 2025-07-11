#!/bin/bash

# AWS FastAPI Diagnostic Script
# Run this if the main fix script fails

echo "🔍 AWS FastAPI Diagnostic Script"
echo "================================"

# Load deployment info
if [ -f "deployment_info.txt" ]; then
    source deployment_info.txt
    echo "✅ Found deployment info"
else
    echo "❌ deployment_info.txt not found"
    exit 1
fi

echo ""
echo "📋 Infrastructure Status:"
echo "   VPC: $VPC_ID"
echo "   EC2: $INSTANCE_ID"
echo "   Public IP: $PUBLIC_IP"
echo "   RDS: $RDS_ENDPOINT"

echo ""
echo "🔍 Step 1: Checking EC2 instance status..."
INSTANCE_STATE=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].State.Name' --output text)
echo "   Instance State: $INSTANCE_STATE"

if [ "$INSTANCE_STATE" != "running" ]; then
    echo "❌ EC2 instance is not running"
    exit 1
fi

echo ""
echo "🔍 Step 2: Testing SSH connectivity..."
if ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no -o ConnectTimeout=10 ec2-user@${PUBLIC_IP} "echo 'SSH OK'" 2>/dev/null; then
    echo "✅ SSH connection successful"
else
    echo "❌ SSH connection failed"
    echo "Check security group rules and key pair"
    exit 1
fi

echo ""
echo "🔍 Step 3: Checking application files on EC2..."
ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
echo "📁 Application directory:"
ls -la /opt/trading-api/ | head -10

echo ""
echo "📝 Environment file status:"
if [ -f "/opt/trading-api/.env" ]; then
    echo "✅ .env file exists"
    echo "File size: $(wc -l < /opt/trading-api/.env) lines"
    echo "First few lines:"
    head -5 /opt/trading-api/.env
else
    echo "❌ .env file missing"
fi

echo ""
echo "🐍 Python dependencies check:"
echo "python-decouple: $(pip3 list | grep decouple || echo 'NOT INSTALLED')"
echo "fastapi: $(pip3 list | grep fastapi || echo 'NOT INSTALLED')"
echo "uvicorn: $(pip3 list | grep uvicorn || echo 'NOT INSTALLED')"

echo ""
echo "📊 Process status:"
ps aux | grep uvicorn | grep -v grep || echo "No uvicorn process running"

echo ""
echo "📄 Log file status:"
if [ -f "/var/log/trading-api/app.log" ]; then
    echo "✅ Log file exists"
    echo "Size: $(wc -l < /var/log/trading-api/app.log) lines"
    echo "Last 10 lines:"
    tail -10 /var/log/trading-api/app.log
else
    echo "❌ Log file missing"
fi
EOF

echo ""
echo "🔍 Step 4: Testing external connectivity..."
echo "Testing health endpoint from local machine..."
if curl -f -s --connect-timeout 10 http://${PUBLIC_IP}:8000/health > /dev/null; then
    echo "✅ Health endpoint accessible externally"
    curl -s http://${PUBLIC_IP}:8000/health
else
    echo "❌ Health endpoint not accessible externally"
    echo "Check security group port 8000 rules"
fi

echo ""
echo "🔍 Step 5: Security group analysis..."
EC2_SG_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)
echo "EC2 Security Group: $EC2_SG_ID"

echo "Security group rules:"
aws ec2 describe-security-groups --group-ids $EC2_SG_ID --query 'SecurityGroups[0].IpPermissions[*].[IpProtocol,FromPort,ToPort,IpRanges[0].CidrIp]' --output table

echo ""
echo "🔍 Step 6: ALB health check..."
echo "Testing ALB endpoint..."
if curl -f -s --connect-timeout 10 http://${ALB_DNS}/health > /dev/null; then
    echo "✅ ALB health endpoint accessible"
else
    echo "❌ ALB health endpoint not accessible"
    echo "ALB may still be initializing or target is unhealthy"
fi

# Check target group health
if [ ! -z "$TARGET_GROUP_ARN" ]; then
    echo ""
    echo "Target group health:"
    aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[*].[Target.Id,TargetHealth.State,TargetHealth.Description]' --output table
fi

echo ""
echo "🔍 Diagnostic Summary:"
echo "======================"
echo "1. EC2 Instance: $INSTANCE_STATE"
echo "2. SSH Access: $(ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no -o ConnectTimeout=5 ec2-user@${PUBLIC_IP} "echo 'OK'" 2>/dev/null || echo 'FAILED')"
echo "3. App Process: $(ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} "ps aux | grep uvicorn | grep -v grep | wc -l" 2>/dev/null) running"
echo "4. Health Check: $(curl -f -s --connect-timeout 5 http://${PUBLIC_IP}:8000/health >/dev/null 2>&1 && echo 'OK' || echo 'FAILED')"
echo "5. ALB Health: $(curl -f -s --connect-timeout 5 http://${ALB_DNS}/health >/dev/null 2>&1 && echo 'OK' || echo 'FAILED')"

echo ""
echo "🔧 Quick fix commands if needed:"
echo "================================"
echo "1. Restart application:"
echo "   ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'cd /opt/trading-api && pkill -f uvicorn && nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /var/log/trading-api/app.log 2>&1 &'"
echo ""
echo "2. View live logs:"
echo "   ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'tail -f /var/log/trading-api/app.log'"
echo ""
echo "3. Install missing dependencies:"
echo "   ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} 'cd /opt/trading-api && pip3 install python-decouple structlog==24.4.0'"
