# Kraken Trading System

A comprehensive MCP (Model Context Protocol) server for cryptocurrency trading through Kraken's WebSocket API.

## Features

- **Real-time Trading**: WebSocket integration with Kraken exchange
- **Order Management**: Advanced order lifecycle management
- **Risk Management**: Comprehensive risk controls and validation
- **Analytics**: Fill processing and performance analytics
- **MCP Integration**: Expose trading capabilities to AI clients like Claude

## Quick Start

### Prerequisites

- Python 3.9+
- Kraken API credentials (for live trading)

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd kraken_trading_system
```

2. Install dependencies:
```bash
pip install -e .
```

3. Install MCP SDK:
```bash
pip install "mcp[cli]"
```

### MCP Server

Start the MCP server for Claude integration:

```bash
# Test with MCP Inspector
mcp dev src/trading_systems/mcp_server/main.py

# Install for Claude Desktop
mcp install src/trading_systems/mcp_server/main.py
```

### Environment Setup

Copy the example environment file and configure your API keys:

```bash
cp env_example.sh .env
# Edit .env with your Kraken API credentials
```

## Project Structure

```
src/trading_systems/
├── mcp_server/           # MCP server implementation
├── exchanges/kraken/     # Kraken exchange integration
├── config/              # Configuration management
├── utils/               # Utilities and logging
└── risk/                # Risk management
```

## Trading System Components

- **WebSocket Client**: Real-time market data and order updates
- **Order Manager**: Order lifecycle and state management
- **Account Manager**: Account data and balance tracking
- **Fill Processor**: Trade execution analytics
- **Risk Validator**: Pre-trade risk checks

## MCP Server Features

The MCP server exposes trading functionality through:

### Tools
- `ping()` - Test connectivity
- `get_server_status()` - System status
- `get_account_balance()` - Account balances

### Resources
- `market://status` - Market status information

### Security

- Demo mode by default (no real trading)
- Configurable risk limits
- Audit logging
- Rate limiting

## Development

### Testing

Run the test suite:
```bash
python test_mcp_server.py
```

### Demo Mode

The system starts in safe demo mode with mock data. To enable real trading:

```python
# In configuration
enable_real_trading = True
```

## License

MIT License - see LICENSE file for details.

## Contributing

See CONTRIBUTING.md for development guidelines.
