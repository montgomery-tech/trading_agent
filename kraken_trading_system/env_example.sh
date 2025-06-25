# Kraken API Configuration
KRAKEN_API_KEY=your_api_key_here
KRAKEN_API_SECRET=your_api_secret_here

# WebSocket Configuration
KRAKEN_WS_PUBLIC_URL=wss://ws.kraken.com
KRAKEN_WS_PRIVATE_URL=wss://ws-auth.kraken.com

# SSL Configuration
SSL_VERIFY_CERTIFICATES=true
SSL_CHECK_HOSTNAME=true

# Trading Configuration
DEFAULT_CURRENCY_PAIR=XBT/USD
MAX_POSITION_SIZE=1.0
MAX_ORDER_VALUE=10000.0

# System Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
ENVIRONMENT=development

# Risk Management
ENABLE_RISK_CHECKS=true
MAX_DAILY_LOSS=1000.0
MAX_OPEN_ORDERS=10

# Testing Configuration (for sandbox/testnet if available)
USE_SANDBOX=true
SANDBOX_API_KEY=sandbox_key_here
SANDBOX_API_SECRET=sandbox_secret_here
