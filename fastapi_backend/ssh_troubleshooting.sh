#!/bin/bash

# SSH Connection Troubleshooting
echo "🔍 SSH Connection Troubleshooting"
echo "=================================="

# Check if key file exists
echo ""
echo "1. Checking SSH key file..."
if [ -f "trading-api-keypair.pem" ]; then
    echo "✅ trading-api-keypair.pem found"
    echo "   File permissions: $(ls -la trading-api-keypair.pem | awk '{print $1}')"
    echo "   File size: $(ls -lh trading-api-keypair.pem | awk '{print $5}')"
else
    echo "❌ trading-api-keypair.pem not found in current directory"
    echo "   Current directory: $(pwd)"
    echo "   Files in directory:"
    ls -la *.pem 2>/dev/null || echo "   No .pem files found"
fi

# Check key permissions
echo ""
echo "2. Checking key file permissions..."
if [ -f "trading-api-keypair.pem" ]; then
    PERMS=$(stat -f "%Mp%Lp" trading-api-keypair.pem 2>/dev/null || stat -c "%a" trading-api-keypair.pem 2>/dev/null)
    echo "   Current permissions: $PERMS"
    
    if [ "$PERMS" != "400" ] && [ "$PERMS" != "0400" ]; then
        echo "⚠️  Key permissions need to be 400"
        echo "   Run: chmod 400 trading-api-keypair.pem"
    else
        echo "✅ Key permissions are correct"
    fi
fi

# Test basic connectivity
echo ""
echo "3. Testing basic connectivity to EC2..."
source deployment_info.txt
echo "   Target IP: $PUBLIC_IP"

echo "   Testing port 22 (SSH):"
if timeout 5 bash -c "</dev/tcp/${PUBLIC_IP}/22" 2>/dev/null; then
    echo "✅ Port 22 is reachable"
else
    echo "❌ Port 22 is not reachable"
    echo "   This could indicate:"
    echo "   - Security group doesn't allow SSH from your IP"
    echo "   - EC2 instance is not running SSH service"
    echo "   - Network connectivity issues"
fi

echo "   Testing port 8000 (Application):"
if timeout 5 bash -c "</dev/tcp/${PUBLIC_IP}/8000" 2>/dev/null; then
    echo "✅ Port 8000 is reachable"
else
    echo "❌ Port 8000 is not reachable"
fi

# Check your public IP
echo ""
echo "4. Your current public IP:"
YOUR_IP=$(curl -s https://ipinfo.io/ip 2>/dev/null || curl -s https://icanhazip.com 2>/dev/null || echo "Could not determine")
echo "   $YOUR_IP"

# Check security groups
echo ""
echo "5. Checking EC2 security group rules..."
if command -v aws >/dev/null 2>&1; then
    echo "   SSH rules (port 22):"
    aws ec2 describe-security-groups --group-ids $EC2_SG_ID --query 'SecurityGroups[0].IpPermissions[?FromPort==`22`].IpRanges[*].CidrIp' --output text
    
    echo "   Application rules (port 8000):"
    aws ec2 describe-security-groups --group-ids $EC2_SG_ID --query 'SecurityGroups[0].IpPermissions[?FromPort==`8000`].IpRanges[*].CidrIp' --output text
else
    echo "   AWS CLI not available - cannot check security groups"
fi

echo ""
echo "6. Suggested fixes:"
echo "   A. Fix key permissions: chmod 400 trading-api-keypair.pem"
echo "   B. Test manual SSH: ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP}"
echo "   C. If still failing, check security group allows your IP ($YOUR_IP) on port 22"
echo "   D. Try SSH with verbose output: ssh -v -i trading-api-keypair.pem ec2-user@${PUBLIC_IP}"
