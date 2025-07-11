#!/bin/bash
# AWS Core Application Deployment Scripts
# Deploys FastAPI trading application to AWS

set -e

# Configuration
REGION="us-east-1"
PROJECT_NAME="trading-api"
KEY_PAIR_NAME="${PROJECT_NAME}-keypair"
VPC_NAME="${PROJECT_NAME}-vpc"
DB_INSTANCE_ID="${PROJECT_NAME}-db"
EC2_INSTANCE_NAME="${PROJECT_NAME}-app"

# Colors for output
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

# Check prerequisites
check_prerequisites() {
    print_step "Checking Prerequisites"

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_status "❌ AWS CLI not found. Please install it first." $RED
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_status "❌ AWS credentials not configured. Run 'aws configure' first." $RED
        exit 1
    fi

    print_status "✅ AWS CLI and credentials configured" $GREEN

    # Show account info
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
    print_status "Account: $ACCOUNT_ID" $YELLOW
    print_status "User: $USER_ARN" $YELLOW
}

# Create SSH key pair
create_key_pair() {
    print_step "Creating SSH Key Pair"

    if aws ec2 describe-key-pairs --key-names $KEY_PAIR_NAME --region $REGION &> /dev/null; then
        print_status "✅ Key pair $KEY_PAIR_NAME already exists" $YELLOW
        return
    fi

    aws ec2 create-key-pair \
        --key-name $KEY_PAIR_NAME \
        --region $REGION \
        --query 'KeyMaterial' \
        --output text > ${KEY_PAIR_NAME}.pem

    chmod 400 ${KEY_PAIR_NAME}.pem
    print_status "✅ Created key pair: ${KEY_PAIR_NAME}.pem" $GREEN
    print_status "⚠️  IMPORTANT: Save this file securely!" $YELLOW
}

# Create VPC and networking
create_vpc() {
    print_step "Creating VPC and Networking"

    # Check if VPC exists
    VPC_ID=$(aws ec2 describe-vpcs \
        --region $REGION \
        --filters "Name=tag:Name,Values=$VPC_NAME" \
        --query 'Vpcs[0].VpcId' \
        --output text 2>/dev/null || echo "None")

    if [ "$VPC_ID" != "None" ] && [ "$VPC_ID" != "null" ]; then
        print_status "✅ VPC already exists: $VPC_ID" $YELLOW
        return
    fi

    # Create VPC
    VPC_ID=$(aws ec2 create-vpc \
        --cidr-block 10.0.0.0/16 \
        --region $REGION \
        --query 'Vpc.VpcId' \
        --output text)

    aws ec2 create-tags \
        --resources $VPC_ID \
        --tags Key=Name,Value=$VPC_NAME \
        --region $REGION

    print_status "✅ Created VPC: $VPC_ID" $GREEN

    # Enable DNS hostnames
    aws ec2 modify-vpc-attribute \
        --vpc-id $VPC_ID \
        --enable-dns-hostnames \
        --region $REGION

    # Create Internet Gateway
    IGW_ID=$(aws ec2 create-internet-gateway \
        --region $REGION \
        --query 'InternetGateway.InternetGatewayId' \
        --output text)

    aws ec2 attach-internet-gateway \
        --internet-gateway-id $IGW_ID \
        --vpc-id $VPC_ID \
        --region $REGION

    aws ec2 create-tags \
        --resources $IGW_ID \
        --tags Key=Name,Value=${PROJECT_NAME}-igw \
        --region $REGION

    print_status "✅ Created Internet Gateway: $IGW_ID" $GREEN

    # Create public subnet
    PUBLIC_SUBNET_ID=$(aws ec2 create-subnet \
        --vpc-id $VPC_ID \
        --cidr-block 10.0.1.0/24 \
        --availability-zone ${REGION}a \
        --region $REGION \
        --query 'Subnet.SubnetId' \
        --output text)

    aws ec2 create-tags \
        --resources $PUBLIC_SUBNET_ID \
        --tags Key=Name,Value=${PROJECT_NAME}-public-subnet \
        --region $REGION

    # Enable auto-assign public IP
    aws ec2 modify-subnet-attribute \
        --subnet-id $PUBLIC_SUBNET_ID \
        --map-public-ip-on-launch \
        --region $REGION

    print_status "✅ Created public subnet: $PUBLIC_SUBNET_ID" $GREEN

    # Create private subnet for RDS
    PRIVATE_SUBNET_ID=$(aws ec2 create-subnet \
        --vpc-id $VPC_ID \
        --cidr-block 10.0.2.0/24 \
        --availability-zone ${REGION}b \
        --region $REGION \
        --query 'Subnet.SubnetId' \
        --output text)

    aws ec2 create-tags \
        --resources $PRIVATE_SUBNET_ID \
        --tags Key=Name,Value=${PROJECT_NAME}-private-subnet \
        --region $REGION

    print_status "✅ Created private subnet: $PRIVATE_SUBNET_ID" $GREEN

    # Create route table for public subnet
    ROUTE_TABLE_ID=$(aws ec2 create-route-table \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query 'RouteTable.RouteTableId' \
        --output text)

    aws ec2 create-route \
        --route-table-id $ROUTE_TABLE_ID \
        --destination-cidr-block 0.0.0.0/0 \
        --gateway-id $IGW_ID \
        --region $REGION

    aws ec2 associate-route-table \
        --subnet-id $PUBLIC_SUBNET_ID \
        --route-table-id $ROUTE_TABLE_ID \
        --region $REGION

    aws ec2 create-tags \
        --resources $ROUTE_TABLE_ID \
        --tags Key=Name,Value=${PROJECT_NAME}-public-rt \
        --region $REGION

    print_status "✅ Configured routing" $GREEN

    # Store VPC info for later use
    echo "VPC_ID=$VPC_ID" > vpc_info.txt
    echo "PUBLIC_SUBNET_ID=$PUBLIC_SUBNET_ID" >> vpc_info.txt
    echo "PRIVATE_SUBNET_ID=$PRIVATE_SUBNET_ID" >> vpc_info.txt
}

# Create security groups
create_security_groups() {
    print_step "Creating Security Groups"

    # Source VPC info
    source vpc_info.txt

    # ALB Security Group
    ALB_SG_ID=$(aws ec2 create-security-group \
        --group-name ${PROJECT_NAME}-alb-sg \
        --description "Security group for Application Load Balancer" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query 'GroupId' \
        --output text)

    aws ec2 authorize-security-group-ingress \
        --group-id $ALB_SG_ID \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region $REGION

    aws ec2 authorize-security-group-ingress \
        --group-id $ALB_SG_ID \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region $REGION

    print_status "✅ Created ALB security group: $ALB_SG_ID" $GREEN

    # EC2 Security Group
    EC2_SG_ID=$(aws ec2 create-security-group \
        --group-name ${PROJECT_NAME}-ec2-sg \
        --description "Security group for EC2 instances" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query 'GroupId' \
        --output text)

    # Allow HTTP from ALB
    aws ec2 authorize-security-group-ingress \
        --group-id $EC2_SG_ID \
        --protocol tcp \
        --port 8000 \
        --source-group $ALB_SG_ID \
        --region $REGION

    # Allow SSH from your IP
    MY_IP=$(curl -s https://ipinfo.io/ip)
    aws ec2 authorize-security-group-ingress \
        --group-id $EC2_SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr ${MY_IP}/32 \
        --region $REGION

    print_status "✅ Created EC2 security group: $EC2_SG_ID" $GREEN
    print_status "   SSH access from: $MY_IP" $YELLOW

    # RDS Security Group
    RDS_SG_ID=$(aws ec2 create-security-group \
        --group-name ${PROJECT_NAME}-rds-sg \
        --description "Security group for RDS database" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query 'GroupId' \
        --output text)

    # Allow PostgreSQL from EC2
    aws ec2 authorize-security-group-ingress \
        --group-id $RDS_SG_ID \
        --protocol tcp \
        --port 5432 \
        --source-group $EC2_SG_ID \
        --region $REGION

    print_status "✅ Created RDS security group: $RDS_SG_ID" $GREEN

    # Store security group info
    echo "ALB_SG_ID=$ALB_SG_ID" >> vpc_info.txt
    echo "EC2_SG_ID=$EC2_SG_ID" >> vpc_info.txt
    echo "RDS_SG_ID=$RDS_SG_ID" >> vpc_info.txt
}

# Create RDS subnet group
create_db_subnet_group() {
    print_step "Creating RDS Subnet Group"

    source vpc_info.txt

    # Create additional subnet in different AZ for RDS
    PRIVATE_SUBNET_2_ID=$(aws ec2 create-subnet \
        --vpc-id $VPC_ID \
        --cidr-block 10.0.3.0/24 \
        --availability-zone ${REGION}c \
        --region $REGION \
        --query 'Subnet.SubnetId' \
        --output text)

    aws ec2 create-tags \
        --resources $PRIVATE_SUBNET_2_ID \
        --tags Key=Name,Value=${PROJECT_NAME}-private-subnet-2 \
        --region $REGION

    # Create DB subnet group
    aws rds create-db-subnet-group \
        --db-subnet-group-name ${PROJECT_NAME}-db-subnet-group \
        --db-subnet-group-description "Subnet group for ${PROJECT_NAME} RDS" \
        --subnet-ids $PRIVATE_SUBNET_ID $PRIVATE_SUBNET_2_ID \
        --region $REGION

    print_status "✅ Created RDS subnet group" $GREEN

    echo "PRIVATE_SUBNET_2_ID=$PRIVATE_SUBNET_2_ID" >> vpc_info.txt
}

# Create RDS PostgreSQL instance
create_rds_instance() {
    print_step "Creating RDS PostgreSQL Instance"

    source vpc_info.txt

    # Check if RDS instance exists
    if aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_ID --region $REGION &> /dev/null; then
        print_status "✅ RDS instance already exists: $DB_INSTANCE_ID" $YELLOW
        return
    fi

    # Generate secure password
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

    print_status "🔐 Generated database password: $DB_PASSWORD" $YELLOW
    print_status "⚠️  IMPORTANT: Save this password securely!" $RED
    echo "DB_PASSWORD=$DB_PASSWORD" >> vpc_info.txt

    # Create RDS instance
    aws rds create-db-instance \
        --db-instance-identifier $DB_INSTANCE_ID \
        --db-instance-class db.t3.micro \
        --engine postgres \
        --engine-version 15.7 \
        --master-username dbadmin \
        --master-user-password "$DB_PASSWORD" \
        --allocated-storage 20 \
        --vpc-security-group-ids $RDS_SG_ID \
        --db-subnet-group-name ${PROJECT_NAME}-db-subnet-group \
        --backup-retention-period 7 \
        --storage-encrypted \
        --region $REGION \
        --db-name balance_tracker

    print_status "✅ RDS instance creation initiated" $GREEN
    print_status "⏳ Instance will take 5-10 minutes to become available" $YELLOW

    # Wait for RDS instance to be available
    print_status "⏳ Waiting for RDS instance to become available..." $YELLOW
    aws rds wait db-instance-available --db-instance-identifier $DB_INSTANCE_ID --region $REGION

    # Get RDS endpoint
    RDS_ENDPOINT=$(aws rds describe-db-instances \
        --db-instance-identifier $DB_INSTANCE_ID \
        --region $REGION \
        --query 'DBInstances[0].Endpoint.Address' \
        --output text)

    print_status "✅ RDS instance available at: $RDS_ENDPOINT" $GREEN
    echo "RDS_ENDPOINT=$RDS_ENDPOINT" >> vpc_info.txt
}

# Create EC2 instance
create_ec2_instance() {
    print_step "Creating EC2 Instance"

    source vpc_info.txt

    # Get latest Amazon Linux 2023 AMI
    AMI_ID=$(aws ec2 describe-images \
        --owners amazon \
        --filters "Name=name,Values=al2023-ami-*-x86_64" \
        --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
        --output text \
        --region $REGION)

    print_status "Using AMI: $AMI_ID" $YELLOW

    # Create user data script
    cat > user_data.sh << 'EOF'
#!/bin/bash
yum update -y
yum install -y python3 python3-pip git postgresql15

# Install Python dependencies
pip3 install fastapi uvicorn python-multipart python-jose cryptography

# Create application user
useradd -m -s /bin/bash appuser

# Create application directory
mkdir -p /opt/trading-api
chown appuser:appuser /opt/trading-api

# Install PM2 globally
npm install -g pm2

echo "EC2 instance setup completed" > /var/log/setup.log
EOF

    # Launch EC2 instance
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $AMI_ID \
        --count 1 \
        --instance-type t3.micro \
        --key-name $KEY_PAIR_NAME \
        --security-group-ids $EC2_SG_ID \
        --subnet-id $PUBLIC_SUBNET_ID \
        --user-data file://user_data.sh \
        --region $REGION \
        --query 'Instances[0].InstanceId' \
        --output text)

    aws ec2 create-tags \
        --resources $INSTANCE_ID \
        --tags Key=Name,Value=$EC2_INSTANCE_NAME \
        --region $REGION

    print_status "✅ EC2 instance launched: $INSTANCE_ID" $GREEN

    # Wait for instance to be running
    print_status "⏳ Waiting for EC2 instance to be running..." $YELLOW
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

    # Get public IP
    PUBLIC_IP=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --region $REGION \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text)

    print_status "✅ EC2 instance running at: $PUBLIC_IP" $GREEN
    echo "INSTANCE_ID=$INSTANCE_ID" >> vpc_info.txt
    echo "PUBLIC_IP=$PUBLIC_IP" >> vpc_info.txt

    # Clean up user data file
    rm user_data.sh
}

# Create Application Load Balancer
create_load_balancer() {
    print_step "Creating Application Load Balancer"

    source vpc_info.txt

    # Create ALB
    ALB_ARN=$(aws elbv2 create-load-balancer \
        --name ${PROJECT_NAME}-alb \
        --subnets $PUBLIC_SUBNET_ID $PRIVATE_SUBNET_2_ID \
        --security-groups $ALB_SG_ID \
        --region $REGION \
        --query 'LoadBalancers[0].LoadBalancerArn' \
        --output text)

    # Get ALB DNS name
    ALB_DNS=$(aws elbv2 describe-load-balancers \
        --load-balancer-arns $ALB_ARN \
        --region $REGION \
        --query 'LoadBalancers[0].DNSName' \
        --output text)

    print_status "✅ Created ALB: $ALB_DNS" $GREEN

    # Create target group
    TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
        --name ${PROJECT_NAME}-targets \
        --protocol HTTP \
        --port 8000 \
        --vpc-id $VPC_ID \
        --health-check-path /health \
        --region $REGION \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text)

    # Register EC2 instance with target group
    aws elbv2 register-targets \
        --target-group-arn $TARGET_GROUP_ARN \
        --targets Id=$INSTANCE_ID \
        --region $REGION

    # Create listener (HTTP for now, HTTPS later with SSL)
    aws elbv2 create-listener \
        --load-balancer-arn $ALB_ARN \
        --protocol HTTP \
        --port 80 \
        --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN \
        --region $REGION

    print_status "✅ ALB configured with target group" $GREEN
    print_status "🌐 Your API will be available at: http://$ALB_DNS" $BLUE

    echo "ALB_ARN=$ALB_ARN" >> vpc_info.txt
    echo "ALB_DNS=$ALB_DNS" >> vpc_info.txt
    echo "TARGET_GROUP_ARN=$TARGET_GROUP_ARN" >> vpc_info.txt
}

# Generate deployment summary
generate_summary() {
    print_step "Deployment Summary"

    source vpc_info.txt

    cat > deployment_summary.txt << EOF
===========================================
AWS Trading API Deployment Summary
===========================================

Infrastructure Created:
- VPC: $VPC_ID
- EC2 Instance: $INSTANCE_ID ($PUBLIC_IP)
- RDS PostgreSQL: $RDS_ENDPOINT
- Load Balancer: $ALB_DNS

Connection Information:
- SSH to EC2: ssh -i ${KEY_PAIR_NAME}.pem ec2-user@$PUBLIC_IP
- Database: postgresql://dbadmin:$DB_PASSWORD@$RDS_ENDPOINT:5432/balance_tracker
- API Endpoint: http://$ALB_DNS

Next Steps:
1. Deploy your FastAPI application to EC2
2. Configure environment variables
3. Set up SSL certificate
4. Import your database schema

Files Generated:
- ${KEY_PAIR_NAME}.pem (SSH private key)
- vpc_info.txt (Infrastructure details)
- deployment_summary.txt (This summary)

Cost Estimate: ~$0-40/month (depending on Free Tier eligibility)
EOF

    print_status "✅ Deployment complete!" $GREEN
    print_status "📄 Summary saved to: deployment_summary.txt" $BLUE

    cat deployment_summary.txt
}

# Main deployment function
deploy_infrastructure() {
    print_status "🚀 Starting AWS Core Application Deployment" $BLUE
    print_status "This will create: VPC, EC2, RDS, and ALB" $YELLOW

    read -p "Continue? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deployment cancelled" $YELLOW
        exit 0
    fi

    check_prerequisites
    create_key_pair
    create_vpc
    create_security_groups
    create_db_subnet_group
    create_rds_instance
    create_ec2_instance
    create_load_balancer
    generate_summary

    print_status "🎉 Infrastructure deployment completed successfully!" $GREEN
}

# Cleanup function
cleanup_infrastructure() {
    print_step "Cleaning Up Infrastructure"

    if [ ! -f vpc_info.txt ]; then
        print_status "❌ No deployment found (vpc_info.txt missing)" $RED
        exit 1
    fi

    source vpc_info.txt

    print_status "⚠️  This will DELETE all infrastructure and data!" $RED
    read -p "Are you sure? Type 'DELETE' to confirm: " confirmation

    if [ "$confirmation" != "DELETE" ]; then
        print_status "Cleanup cancelled" $YELLOW
        exit 0
    fi

    # Delete ALB
    if [ ! -z "$ALB_ARN" ]; then
        aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN --region $REGION
        print_status "✅ Deleted ALB" $GREEN
    fi

    # Delete target group
    if [ ! -z "$TARGET_GROUP_ARN" ]; then
        aws elbv2 delete-target-group --target-group-arn $TARGET_GROUP_ARN --region $REGION
        print_status "✅ Deleted target group" $GREEN
    fi

    # Terminate EC2 instance
    if [ ! -z "$INSTANCE_ID" ]; then
        aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $REGION
        aws ec2 wait instance-terminated --instance-ids $INSTANCE_ID --region $REGION
        print_status "✅ Terminated EC2 instance" $GREEN
    fi

    # Delete RDS instance
    if [ ! -z "$DB_INSTANCE_ID" ]; then
        aws rds delete-db-instance \
            --db-instance-identifier $DB_INSTANCE_ID \
            --skip-final-snapshot \
            --region $REGION
        print_status "✅ Deleting RDS instance (this may take several minutes)" $GREEN
    fi

    # Delete VPC and associated resources
    if [ ! -z "$VPC_ID" ]; then
        # Delete security groups, subnets, etc. (add more cleanup as needed)
        aws ec2 delete-vpc --vpc-id $VPC_ID --region $REGION
        print_status "✅ Deleted VPC" $GREEN
    fi

    # Delete key pair
    aws ec2 delete-key-pair --key-name $KEY_PAIR_NAME --region $REGION
    rm -f ${KEY_PAIR_NAME}.pem
    print_status "✅ Deleted key pair" $GREEN

    # Clean up local files
    rm -f vpc_info.txt deployment_summary.txt

    print_status "🧹 Cleanup completed" $GREEN
}

# Command line interface
case "${1:-deploy}" in
    "deploy")
        deploy_infrastructure
        ;;
    "cleanup")
        cleanup_infrastructure
        ;;
    "status")
        if [ -f vpc_info.txt ]; then
            cat deployment_summary.txt
        else
            print_status "No deployment found" $YELLOW
        fi
        ;;
    *)
        echo "Usage: $0 [deploy|cleanup|status]"
        echo "  deploy  - Deploy infrastructure (default)"
        echo "  cleanup - Delete all infrastructure"
        echo "  status  - Show deployment status"
        exit 1
        ;;
esac
