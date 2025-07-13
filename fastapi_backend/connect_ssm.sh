#!/bin/bash
# Quick SSM connection script
echo "🔗 Connecting to EC2 via SSM Session Manager..."
echo "Instance: i-0152b8b9330ba51f0"
echo ""
aws ssm start-session --target i-0152b8b9330ba51f0
