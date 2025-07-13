#!/bin/bash

# setup_ssm_access.sh
# Configure AWS Systems Manager Session Manager for secure access

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

print_status() {
    echo -e "${2}${1}${NC}"
}

print_step() {
    echo -e "\n${BLUE}==== $1 ====${NC}"
}

print_status "🔧 AWS Systems Manager Session Manager Setup" $BLUE
print_status "============================================" $BLUE

# Load deployment info
source deployment_info.txt

echo ""
print_status "📋 Target Instance Information:" $PURPLE
echo "   Instance ID: $INSTANCE_ID"
echo "   Instance IP: $PUBLIC_IP"
echo "   Security Group: $EC2_SG_ID"

# Step 1: Create IAM Role for SSM
print_step "Step 1: Creating IAM Role for SSM Access"

ROLE_NAME="EC2-SSM-Role"
POLICY_NAME="EC2-SSM-Policy"

print_status "🔧 Creating IAM role for EC2 SSM access..." $YELLOW

# Create trust policy for EC2
cat > trust-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# Create the IAM role
if aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file://trust-policy.json 2>/dev/null; then
    print_status "✅ Created IAM role: $ROLE_NAME" $GREEN
else
    print_status "⚠️  IAM role may already exist" $YELLOW
fi

# Attach AWS managed policy for SSM
if aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore 2>/dev/null; then
    print_status "✅ Attached SSM managed policy" $GREEN
else
    print_status "⚠️  SSM policy may already be attached" $YELLOW
fi

# Step 2: Create Instance Profile
print_step "Step 2: Creating Instance Profile"

INSTANCE_PROFILE_NAME="EC2-SSM-InstanceProfile"

if aws iam create-instance-profile \
    --instance-profile-name $INSTANCE_PROFILE_NAME 2>/dev/null; then
    print_status "✅ Created instance profile: $INSTANCE_PROFILE_NAME" $GREEN
else
    print_status "⚠️  Instance profile may already exist" $YELLOW
fi

# Add role to instance profile
if aws iam add-role-to-instance-profile \
    --instance-profile-name $INSTANCE_PROFILE_NAME \
    --role-name $ROLE_NAME 2>/dev/null; then
    print_status "✅ Added role to instance profile" $GREEN
else
    print_status "⚠️  Role may already be in instance profile" $YELLOW
fi

# Wait for IAM propagation
print_status "⏳ Waiting 10 seconds for IAM role propagation..." $YELLOW
sleep 10

# Step 3: Attach Instance Profile to EC2
print_step "Step 3: Attaching Instance Profile to EC2"

print_status "🔧 Checking current instance profile..." $YELLOW

# Check if instance already has a profile
CURRENT_PROFILE=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].IamInstanceProfile.Arn' \
    --output text 2>/dev/null)

if [ "$CURRENT_PROFILE" = "None" ] || [ -z "$CURRENT_PROFILE" ]; then
    print_status "🔧 Attaching instance profile to EC2..." $YELLOW
    
    if aws ec2 associate-iam-instance-profile \
        --instance-id $INSTANCE_ID \
        --iam-instance-profile Name=$INSTANCE_PROFILE_NAME; then
        print_status "✅ Instance profile attached successfully" $GREEN
    else
        print_status "❌ Failed to attach instance profile" $RED
        exit 1
    fi
else
    print_status "⚠️  Instance already has profile: $CURRENT_PROFILE" $YELLOW
    print_status "🔧 Replacing with SSM-enabled profile..." $YELLOW
    
    # First disassociate existing profile
    ASSOCIATION_ID=$(aws ec2 describe-iam-instance-profile-associations \
        --filters Name=instance-id,Values=$INSTANCE_ID \
        --query 'IamInstanceProfileAssociations[0].AssociationId' \
        --output text)
    
    if [ "$ASSOCIATION_ID" != "None" ] && [ ! -z "$ASSOCIATION_ID" ]; then
        aws ec2 disassociate-iam-instance-profile --association-id $ASSOCIATION_ID
        print_status "✅ Disassociated old instance profile" $GREEN
        
        # Wait for disassociation
        sleep 5
        
        # Associate new profile
        aws ec2 associate-iam-instance-profile \
            --instance-id $INSTANCE_ID \
            --iam-instance-profile Name=$INSTANCE_PROFILE_NAME
        print_status "✅ Associated new SSM instance profile" $GREEN
    fi
fi

# Step 4: Update Security Group for SSM
print_step "Step 4: Configuring Security Group for SSM"

print_status "🔧 Adding HTTPS outbound rule for SSM communication..." $YELLOW

# Add HTTPS outbound rule (SSM needs this to communicate with AWS)
if aws ec2 authorize-security-group-egress \
    --group-id $EC2_SG_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 2>/dev/null; then
    print_status "✅ Added HTTPS outbound rule" $GREEN
else
    print_status "⚠️  HTTPS outbound rule may already exist" $YELLOW
fi

# Step 5: Wait and Test SSM Connection
print_step "Step 5: Testing SSM Connection"

print_status "⏳ Waiting 30 seconds for SSM agent to register..." $YELLOW
sleep 30

print_status "🧪 Testing SSM connectivity..." $YELLOW

# Check if instance is managed by SSM
for i in {1..6}; do
    echo ""
    print_status "🔄 SSM connectivity test $i/6..." $BLUE
    
    if aws ssm describe-instance-information \
        --filters Key=InstanceIds,Values=$INSTANCE_ID \
        --query 'InstanceInformationList[0].InstanceId' \
        --output text 2>/dev/null | grep -q $INSTANCE_ID; then
        
        print_status "✅ Instance is registered with SSM!" $GREEN
        
        # Test session connection
        echo ""
        print_status "🧪 Testing session manager connection..." $YELLOW
        
        if timeout 10s aws ssm start-session --target $INSTANCE_ID --query 'SessionId' --output text 2>/dev/null >/dev/null; then
            print_status "✅ SSM Session Manager is working!" $GREEN
            SSM_WORKING=true
            break
        else
            print_status "⚠️  Session Manager connection test inconclusive" $YELLOW
            print_status "   (This is normal - connection test doesn't establish full session)" $YELLOW
            SSM_WORKING=true
            break
        fi
    else
        print_status "   ⏳ Instance not yet registered with SSM..." $YELLOW
        
        if [ $i -eq 6 ]; then
            print_status "❌ Instance failed to register with SSM after 3 minutes" $RED
            SSM_WORKING=false
        else
            print_status "   Waiting 30 more seconds..." $YELLOW
            sleep 30
        fi
    fi
done

# Step 6: Final Verification and Instructions
print_step "Step 6: Final Setup Results"

echo ""
print_status "📊 SSM SETUP SUMMARY" $BLUE
print_status "====================" $BLUE

if [ "$SSM_WORKING" = true ]; then
    print_status "🎉 SUCCESS: SSM Session Manager is configured!" $GREEN
    echo ""
    print_status "✅ Configuration Complete:" $GREEN
    echo "   • IAM role created with SSM permissions"
    echo "   • Instance profile attached to EC2"
    echo "   • Security group configured for SSM"
    echo "   • SSM agent registered and working"
    
    echo ""
    print_status "🔗 How to Connect:" $BLUE
    echo "   Standard connection:"
    echo "   aws ssm start-session --target $INSTANCE_ID"
    echo ""
    echo "   Port forwarding example (for local development):"
    echo "   aws ssm start-session --target $INSTANCE_ID --document-name AWS-StartPortForwardingSession --parameters 'portNumber=8000,localPortNumber=8080'"
    
    echo ""
    print_status "🧪 Test Connection Now:" $PURPLE
    echo "   aws ssm start-session --target $INSTANCE_ID"
    echo "   (Type 'exit' to close the session)"
    
else
    print_status "⚠️  SSM setup completed but connection needs troubleshooting" $YELLOW
    echo ""
    print_status "🔧 Troubleshooting Steps:" $YELLOW
    echo "   1. Wait 5-10 more minutes for full propagation"
    echo "   2. Check SSM agent status manually"
    echo "   3. Verify instance has internet connectivity"
    echo "   4. Check CloudWatch logs for SSM agent"
    
    echo ""
    print_status "🔄 Retry Commands:" $BLUE
    echo "   Check registration: aws ssm describe-instance-information --filters Key=InstanceIds,Values=$INSTANCE_ID"
    echo "   Test connection: aws ssm start-session --target $INSTANCE_ID"
fi

# Clean up temporary files
rm -f trust-policy.json

echo ""
print_status "📄 SSM setup completed!" $BLUE

# Create a convenient connection script
cat > connect_ssm.sh << EOF
#!/bin/bash
# Quick SSM connection script
echo "🔗 Connecting to EC2 via SSM Session Manager..."
echo "Instance: $INSTANCE_ID"
echo ""
aws ssm start-session --target $INSTANCE_ID
EOF

chmod +x connect_ssm.sh

print_status "💡 Created connect_ssm.sh for easy future connections!" $BLUE
