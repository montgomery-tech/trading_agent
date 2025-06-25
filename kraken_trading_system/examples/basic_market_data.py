"""
Basic example demonstrating Kraken WebSocket public connection and message handling.

This example shows how to:
1. Connect to Kraken's public WebSocket
2. Listen for system status and heartbeat messages
3. Handle connection events
4. Gracefully disconnect

Run this example to verify the WebSocket connection is working properly.
"""

import asyncio
import signal
import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading_system.exchanges.kraken.websocket_client import KrakenWebSocketClient
from trading_system.utils.logger import get_logger


class BasicMarketDataExample:
    """Basic market data connection example."""
    
    def __init__(self):
        self.logger = get_logger("BasicMarketDataExample")
        self.client = KrakenWebSocketClient()
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info("Shutdown signal received", signal=signum)
        self.running = False
    
    async def run(self):
        """Run the basic market data example."""
        try:
            self.logger.info("Starting basic market data example")
            
            # Connect to public WebSocket
            self.logger.info("Connecting to Kraken public WebSocket...")
            await self.client.connect_public()
            self.logger.info("Connected successfully!")
            
            # Display connection status
            status = self.client.get_connection_status()
            self.logger.info("Connection status", **status)
            
            # Listen for messages
            self.logger.info("Listening for messages (Press Ctrl+C to stop)...")
            await self._listen_for_messages()
            
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        except Exception as e:
            self.logger.error("Error in example", error=str(e), exc_info=True)
        finally:
            await self._cleanup()
    
    async def _listen_for_messages(self):
        """Listen for and display incoming WebSocket messages."""
        message_count = 0
        max_messages = 50  # Limit messages for demo
        
        try:
            async for message in self.client.listen_public():
                if not self.running:
                    break
                
                message_count += 1
                
                # Display different message types
                if isinstance(message, dict):
                    event = message.get("event", "unknown")
                    
                    if event == "systemStatus":
                        self.logger.info(
                            "System Status",
                            status=message.get("status"),
                            version=message.get("version"),
                            connection_id=message.get("connectionID")
                        )
                    elif event == "heartbeat":
                        self.logger.info("Heartbeat received")
                    elif event == "subscriptionStatus":
                        self.logger.info(
                            "Subscription Status",
                            status=message.get("status"),
                            channel=message.get("channelName"),
                            pair=message.get("pair")
                        )
                    else:
                        self.logger.info(
                            "Received message",
                            event=event,
                            message_number=message_count
                        )
                
                # Stop after max messages for demo
                if message_count >= max_messages:
                    self.logger.info(f"Received {max_messages} messages, stopping demo")
                    break
                
                # Small delay to avoid overwhelming the console
                await asyncio.sleep(0.1)
        
        except Exception as e:
            self.logger.error("Error listening for messages", error=str(e))
    
    async def _cleanup(self):
        """Clean up resources."""
        self.logger.info("Cleaning up...")
        try:
            await self.client.disconnect()
            self.logger.info("Disconnected from WebSocket")
        except Exception as e:
            self.logger.error("Error during cleanup", error=str(e))


async def main():
    """Main function to run the example."""
    example = BasicMarketDataExample()
    await example.run()


if __name__ == "__main__":
    print("=" * 60)
    print("Kraken Trading System - Basic Market Data Example")
    print("=" * 60)
    print()
    print("This example demonstrates:")
    print("• Connecting to Kraken's public WebSocket")
    print("• Receiving system status and heartbeat messages")
    print("• Handling connection events")
    print("• Graceful shutdown")
    print()
    print("Press Ctrl+C to stop the example")
    print("=" * 60)
    print()
    
    # Run the example
    asyncio.run(main())
