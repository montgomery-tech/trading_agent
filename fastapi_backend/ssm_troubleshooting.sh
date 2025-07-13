#!/bin/bash

# ssm_troubleshooting.sh
# Troubleshoot SSM agent registration issues

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${2}${1}${NC}"
}

print_step() {
    echo -e "\n${BLUE}==== $1 ====${NC}"
}

print_status "🔍 SSM Agent Troubleshooting" $BLUE
print_status "============================" $BLUE

# Load deployment info
source deployment_info.txt

print_step "Step 1: Check Current Registration Status"

print_status "🔍 Checking if instance is registered with SSM..." $YELLOW
SSM_REGISTERED=$(aws ssm describe-instance-information \
    --filters Key=InstanceIds,Values=$INSTANCE_ID \
    --query 'InstanceInformationList[0].InstanceId' \
    --output text 2>/dev/null)

if [ "$SSM_REGISTERED" = "$INSTANCE_ID" ]; then
    print_status "✅ Instance IS registered with SSM!" $GREEN
    echo "Registration details:"
    aws ssm describe-instance-information \
        --filters Key=InstanceIds,Values=$INSTANCE_ID \
        --query 'InstanceInformationList[0].[InstanceId,PingStatus,LastPingDateTime,AgentVersion]' \
        --output table
    
    print_status "🧪 Testing session connection..." $YELLOW
    if timeout 5s aws ssm start-session --target $INSTANCE_ID >/dev/null 2>&1; then
        print_status "✅ SSM Session Manager is working!" $GREEN
        echo ""
        print_status "🎉 SSM IS READY TO USE!" $GREEN
        echo "Connect with: aws ssm start-session --target $INSTANCE_ID"
        exit 0
    fi
else
    print_status "❌ Instance not registered with SSM yet" $RED
fi

print_step "Step 2: Check Instance Profile Association"

print_status "🔍 Verifying instance profile association..." $YELLOW
PROFILE_STATUS=$(aws ec2 describe-iam-instance-profile-associations \
    --filters Name=instance-id,Values=$INSTANCE_ID \
    --query 'IamInstanceProfileAssociations[0].State' \
    --output text 2>/dev/null)

echo "Instance Profile Association Status: $PROFILE_STATUS"

if [ "$PROFILE_STATUS" != "associated" ]; then
    print_status "⚠️  Instance profile not fully associated yet" $YELLOW
    print_status "   Waiting 30 seconds and checking again..." $YELLOW
    sleep 30
    
    PROFILE_STATUS=$(aws ec2 describe-iam-instance-profile-associations \
        --filters Name=instance-id,Values=$INSTANCE_ID \
        --query 'IamInstanceProfileAssociations[0].State' \
        --output text 2>/dev/null)
    
    if [ "$PROFILE_STATUS" = "associated" ]; then
        print_status "✅ Instance profile now associated" $GREEN
    else
        print_status "❌ Instance profile still not associated" $RED
    fi
fi

print_step "Step 3: Check Internet Connectivity"

print_status "🌐 Testing instance internet connectivity..." $YELLOW
print_status "(We need to use SSH temporarily to check SSM agent status)" $YELLOW

# Check if we can SSH (we need this to troubleshoot SSM)
if ! timeout 5 bash -c "</dev/tcp/${PUBLIC_IP}/22" 2>/dev/null; then
    print_status "⚠️  SSH port not reachable. Adding temporary SSH access..." $YELLOW
    
    # Get current IP and add to security group
    CURRENT_IP=$(curl -s https://ipinfo.io/ip 2>/dev/null)
    
    aws ec2 authorize-security-group-ingress \
        --group-id $EC2_SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr ${CURRENT_IP}/32 2>/dev/null || echo "SSH rule may already exist"
    
    print_status "✅ Added temporary SSH access for $CURRENT_IP" $GREEN
    print_status "⏳ Waiting 10 seconds for security group to propagate..." $YELLOW
    sleep 10
fi

print_step "Step 4: Check SSM Agent Status on Instance"

print_status "🔍 Connecting to instance to check SSM agent..." $YELLOW

if ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no -o ConnectTimeout=15 ec2-user@${PUBLIC_IP} bash << 'EOF'
echo "🔍 Checking SSM agent status..."

# Check if SSM agent is running
echo "SSM Agent service status:"
sudo systemctl status amazon-ssm-agent | head -10

echo ""
echo "SSM Agent process:"
ps aux | grep amazon-ssm-agent | head -3

echo ""
echo "Internet connectivity test:"
curl -s --connect-timeout 5 https://ssm.us-east-1.amazonaws.com > /dev/null && echo "✅ Can reach SSM endpoint" || echo "❌ Cannot reach SSM endpoint"

echo ""
echo "Instance metadata check:"
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" -s)
INSTANCE_ID=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" -s http://169.254.169.254/latest/meta-data/instance-id)
echo "Instance ID from metadata: $INSTANCE_ID"

echo ""
echo "IAM role from metadata:"
curl -H "X-aws-ec2-metadata-token: $TOKEN" -s http://169.254.169.254/latest/meta-data/iam/security-credentials/ 2>/dev/null || echo "No IAM role attached"

echo ""
echo "SSM agent logs (last 10 lines):"
sudo tail -10 /var/log/amazon/ssm/amazon-ssm-agent.log 2>/dev/null || echo "SSM log file not found"

EOF
then
    print_status "✅ Successfully checked SSM agent status" $GREEN
else
    print_status "❌ Could not connect to instance via SSH" $RED
    echo "Please check:"
    echo "1. SSH key permissions: chmod 400 trading-api-keypair.pem"
    echo "2. Security group allows SSH from your IP"
    echo "3. Instance is running and reachable"
fi

print_step "Step 5: Restart SSM Agent"

print_status "🔄 Restarting SSM agent to force re-registration..." $YELLOW

ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
echo "🔄 Restarting SSM agent..."
sudo systemctl restart amazon-ssm-agent

echo "⏳ Waiting 10 seconds..."
sleep 10

echo "📊 SSM agent status after restart:"
sudo systemctl status amazon-ssm-agent | head -5

echo "✅ SSM agent restart completed"
EOF

print_step "Step 6: Wait and Test Registration Again"

print_status "⏳ Waiting 60 seconds for SSM agent to register after restart..." $YELLOW
sleep 60

print_status "🧪 Testing SSM registration again..." $YELLOW

for i in {1..3}; do
    echo ""
    print_status "🔄 Registration test $i/3..." $BLUE
    
    SSM_CHECK=$(aws ssm describe-instance-information \
        --filters Key=InstanceIds,Values=$INSTANCE_ID \
        --query 'InstanceInformationList[0].InstanceId' \
        --output text 2>/dev/null)
    
    if [ "$SSM_CHECK" = "$INSTANCE_ID" ]; then
        print_status "✅ Instance is now registered with SSM!" $GREEN
        
        echo "Registration details:"
        aws ssm describe-instance-information \
            --filters Key=InstanceIds,Values=$INSTANCE_ID \
            --query 'InstanceInformationList[0].[InstanceId,PingStatus,LastPingDateTime,AgentVersion]' \
            --output table
        
        print_status "🧪 Testing session connection..." $YELLOW
        if aws ssm start-session --target $INSTANCE_ID --query 'SessionId' --output text >/dev/null 2>&1; then
            print_status "✅ SSM Session Manager is working!" $GREEN
        fi
        
        break
    else
        print_status "   ⏳ Still not registered..." $YELLOW
        if [ $i -lt 3 ]; then
            sleep 30
        fi
    fi
done

print_step "Final Status and Next Steps"

echo ""
print_status "📊 FINAL SSM STATUS" $BLUE
print_status "===================" $BLUE

FINAL_SSM_CHECK=$(aws ssm describe-instance-information \
    --filters Key=InstanceIds,Values=$INSTANCE_ID \
    --query 'InstanceInformationList[0].InstanceId' \
    --output text 2>/dev/null)

if [ "$FINAL_SSM_CHECK" = "$INSTANCE_ID" ]; then
    print_status "🎉 SUCCESS: SSM is now working!" $GREEN
    echo ""
    echo "Connect to your instance:"
    echo "   aws ssm start-session --target $INSTANCE_ID"
    echo ""
    echo "Or use the generated script:"
    echo "   ./connect_ssm.sh"
    
    echo ""
    print_status "🚀 Ready to continue with deployment verification!" $GREEN
    
else
    print_status "⚠️  SSM still not working" $YELLOW
    echo ""
    echo "Manual troubleshooting options:"
    echo "1. Wait another 10-15 minutes for full AWS propagation"
    echo "2. Try rebooting the EC2 instance"
    echo "3. Check CloudWatch logs for detailed SSM agent errors"
    echo "4. Use SSH access for now and set up SSM later"
    
    echo ""
    print_status "🔄 Alternative: Continue with SSH access" $BLUE
    echo "You can proceed with deployment verification using SSH while SSM stabilizes"
fi

echo ""
print_status "🔧 SSM troubleshooting completed!" $BLUE
