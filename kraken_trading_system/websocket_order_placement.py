#!/usr/bin/env python3
"""
WebSocket Order Placement Implementation

Add real order placement functionality to the Kraken WebSocket client
using Kraken's addOrder endpoint via WebSocket.

Based on Kraken WebSocket API documentation:
- Orders are placed via authenticated WebSocket connection
- Uses addOrder event with token authentication
- Receives addOrderStatus response with order details
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, Union
from decimal import Decimal


def add_websocket_order_placement_methods():
    """Add order placement methods to the WebSocket client."""
    
    print("🚀 IMPLEMENTING WEBSOCKET ORDER PLACEMENT")
    print("=" * 60)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ WebSocket client file not found: {websocket_path}")
        return False
    except Exception as e:
        print(f"❌ Error reading WebSocket client: {e}")
        return False
    
    # Check if order placement methods already exist
    if 'async def place_market_order(' in content:
        print("✅ Order placement methods already exist")
        return True
    
    print("🔧 Adding WebSocket order placement methods...")
    
    # Order placement methods to add
    order_placement_methods = '''
    # ===== WEBSOCKET ORDER PLACEMENT METHODS =====
    
    async def place_market_order(self, pair: str, side: str, volume: Union[str, Decimal], 
                                userref: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """
        Place a market order via WebSocket.
        
        Args:
            pair: Trading pair (e.g., "ETH/USD")
            side: Order side ("buy" or "sell")  
            volume: Order volume
            userref: Optional user reference number
            **kwargs: Additional order parameters
            
        Returns:
            Order placement response
            
        Raises:
            WebSocketError: If not connected or order fails
            AuthenticationError: If no valid token
        """
        if not self.is_private_connected or not self.current_token:
            raise WebSocketError("Private WebSocket not connected or no auth token")
        
        # Build order message according to Kraken WebSocket API
        order_message = {
            "event": "addOrder",
            "token": self.current_token,
            "pair": pair,
            "type": side.lower(),
            "ordertype": "market",
            "volume": str(volume)
        }
        
        # Add optional parameters
        if userref is not None:
            order_message["userref"] = str(userref)
        
        # Add any additional parameters
        order_message.update(kwargs)
        
        self.log_info(
            "Placing market order via WebSocket",
            pair=pair,
            side=side,
            volume=str(volume),
            userref=userref
        )
        
        try:
            # Send order via WebSocket
            await self.send_private_message(order_message)
            
            # Wait for response (addOrderStatus)
            response = await self._wait_for_order_response()
            
            if response.get("status") == "ok":
                order_id = response.get("txid")
                description = response.get("descr", "")
                
                self.log_info(
                    "Market order placed successfully",
                    order_id=order_id,
                    description=description
                )
                
                # Register order with OrderManager if available
                if self.order_manager and order_id:
                    await self._register_order_with_manager(order_id, order_message, response)
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "description": description,
                    "response": response
                }
            else:
                error_msg = response.get("errorMessage", "Unknown error")
                self.log_error("Market order failed", error=error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "response": response
                }
                
        except Exception as e:
            self.log_error("Market order placement failed", error=e)
            raise WebSocketError(f"Order placement failed: {e}")
    
    async def place_limit_order(self, pair: str, side: str, volume: Union[str, Decimal],
                               price: Union[str, Decimal], userref: Optional[int] = None,
                               **kwargs) -> Dict[str, Any]:
        """
        Place a limit order via WebSocket.
        
        Args:
            pair: Trading pair (e.g., "ETH/USD")
            side: Order side ("buy" or "sell")
            volume: Order volume
            price: Limit price
            userref: Optional user reference number
            **kwargs: Additional order parameters
            
        Returns:
            Order placement response
        """
        if not self.is_private_connected or not self.current_token:
            raise WebSocketError("Private WebSocket not connected or no auth token")
        
        order_message = {
            "event": "addOrder",
            "token": self.current_token,
            "pair": pair,
            "type": side.lower(),
            "ordertype": "limit",
            "volume": str(volume),
            "price": str(price)
        }
        
        if userref is not None:
            order_message["userref"] = str(userref)
        
        order_message.update(kwargs)
        
        self.log_info(
            "Placing limit order via WebSocket",
            pair=pair,
            side=side,
            volume=str(volume),
            price=str(price),
            userref=userref
        )
        
        try:
            await self.send_private_message(order_message)
            response = await self._wait_for_order_response()
            
            if response.get("status") == "ok":
                order_id = response.get("txid")
                description = response.get("descr", "")
                
                self.log_info(
                    "Limit order placed successfully",
                    order_id=order_id,
                    description=description
                )
                
                if self.order_manager and order_id:
                    await self._register_order_with_manager(order_id, order_message, response)
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "description": description,
                    "response": response
                }
            else:
                error_msg = response.get("errorMessage", "Unknown error")
                self.log_error("Limit order failed", error=error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "response": response
                }
                
        except Exception as e:
            self.log_error("Limit order placement failed", error=e)
            raise WebSocketError(f"Order placement failed: {e}")
    
    async def cancel_order(self, order_ids: Union[str, list], **kwargs) -> Dict[str, Any]:
        """
        Cancel one or more orders via WebSocket.
        
        Args:
            order_ids: Order ID(s) to cancel (string or list)
            **kwargs: Additional parameters
            
        Returns:
            Cancellation response
        """
        if not self.is_private_connected or not self.current_token:
            raise WebSocketError("Private WebSocket not connected or no auth token")
        
        # Ensure order_ids is a list
        if isinstance(order_ids, str):
            order_ids = [order_ids]
        
        cancel_message = {
            "event": "cancelOrder",
            "token": self.current_token,
            "txid": order_ids
        }
        
        cancel_message.update(kwargs)
        
        self.log_info("Cancelling orders via WebSocket", order_ids=order_ids)
        
        try:
            await self.send_private_message(cancel_message)
            response = await self._wait_for_cancel_response()
            
            if response.get("status") == "ok":
                self.log_info("Orders cancelled successfully", order_ids=order_ids)
                return {
                    "success": True,
                    "cancelled_orders": order_ids,
                    "response": response
                }
            else:
                error_msg = response.get("errorMessage", "Unknown error")
                self.log_error("Order cancellation failed", error=error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "response": response
                }
                
        except Exception as e:
            self.log_error("Order cancellation failed", error=e)
            raise WebSocketError(f"Order cancellation failed: {e}")
    
    async def _wait_for_order_response(self, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Wait for addOrderStatus response from WebSocket.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Order status response
        """
        import asyncio
        
        try:
            # Wait for addOrderStatus message
            timeout_time = asyncio.get_event_loop().time() + timeout
            
            while asyncio.get_event_loop().time() < timeout_time:
                try:
                    # Check if we have messages in the queue
                    if not self.private_message_queue.empty():
                        message = self.private_message_queue.get_nowait()
                        
                        if isinstance(message, dict) and message.get("event") == "addOrderStatus":
                            return message
                    
                    # Wait a bit before checking again
                    await asyncio.sleep(0.1)
                    
                except asyncio.QueueEmpty:
                    continue
            
            raise TimeoutError("Timeout waiting for order response")
            
        except Exception as e:
            self.log_error("Error waiting for order response", error=e)
            raise
    
    async def _wait_for_cancel_response(self, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Wait for cancelOrderStatus response from WebSocket.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Cancel status response
        """
        import asyncio
        
        try:
            timeout_time = asyncio.get_event_loop().time() + timeout
            
            while asyncio.get_event_loop().time() < timeout_time:
                try:
                    if not self.private_message_queue.empty():
                        message = self.private_message_queue.get_nowait()
                        
                        if isinstance(message, dict) and message.get("event") == "cancelOrderStatus":
                            return message
                    
                    await asyncio.sleep(0.1)
                    
                except asyncio.QueueEmpty:
                    continue
            
            raise TimeoutError("Timeout waiting for cancel response")
            
        except Exception as e:
            self.log_error("Error waiting for cancel response", error=e)
            raise
    
    async def _register_order_with_manager(self, order_id: str, order_request: Dict[str, Any], 
                                          order_response: Dict[str, Any]) -> None:
        """
        Register a new order with the OrderManager.
        
        Args:
            order_id: The order ID from Kraken
            order_request: Original order request message
            order_response: Order placement response
        """
        try:
            if not self.order_manager:
                return
            
            # Create order creation request from WebSocket order
            from ..order_models import OrderCreationRequest, OrderSide, OrderType
            
            # Map WebSocket parameters to OrderCreationRequest
            side = OrderSide.BUY if order_request["type"].lower() == "buy" else OrderSide.SELL
            order_type = OrderType.MARKET if order_request["ordertype"] == "market" else OrderType.LIMIT
            
            creation_request = OrderCreationRequest(
                pair=order_request["pair"],
                side=side,
                order_type=order_type,
                volume=Decimal(order_request["volume"]),
                price=Decimal(order_request.get("price", "0")) if order_request.get("price") else None,
                userref=order_request.get("userref")
            )
            
            # Create order in OrderManager
            order = await self.order_manager.create_order(creation_request)
            
            # Update with Kraken order ID
            order.kraken_order_id = order_id
            order.status = "submitted"
            
            self.log_info(
                "Order registered with OrderManager",
                order_id=order_id,
                manager_order_id=order.order_id
            )
            
        except Exception as e:
            self.log_error("Failed to register order with OrderManager", error=e, order_id=order_id)
    
    # ===== END ORDER PLACEMENT METHODS =====
'''
    
    # Find a good place to insert the methods (before disconnect method)
    if 'async def disconnect(self' in content:
        # Insert before disconnect method
        disconnect_pos = content.find('async def disconnect(self')
        # Find the start of the method (beginning of line)
        method_start = content.rfind('\n    ', 0, disconnect_pos)
        if method_start == -1:
            method_start = disconnect_pos
        
        new_content = content[:method_start] + order_placement_methods + '\n' + content[method_start:]
    else:
        # Insert near the end of the class
        new_content = content + order_placement_methods
    
    try:
        with open(websocket_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ Added WebSocket order placement methods")
        return True
    except Exception as e:
        print(f"❌ Error writing WebSocket client: {e}")
        return False


def update_live_order_placement_script():
    """Update the live order placement script to use WebSocket order placement."""
    
    print("\n🔧 UPDATING LIVE ORDER PLACEMENT SCRIPT")
    print("=" * 60)
    
    live_order_path = Path("live_order_placement.py")
    
    try:
        with open(live_order_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ Live order placement script not found: {live_order_path}")
        return False
    except Exception as e:
        print(f"❌ Error reading live order placement script: {e}")
        return False
    
    # Find the section that needs to be replaced
    simulation_start = content.find('print("   ⚠️ ACTUAL ORDER PLACEMENT CODE NOT IMPLEMENTED")')
    if simulation_start == -1:
        print("❌ Could not find simulation code section to replace")
        return False
    
    # Find the end of the simulation section
    simulation_end = content.find('await self._simulate_order_placement()', simulation_start)
    if simulation_end == -1:
        print("❌ Could not find end of simulation section")
        return False
    
    # Find the end of that line
    line_end = content.find('\n', simulation_end)
    
    # Replace simulation with real order placement
    real_order_code = '''try:
                # Place actual market order via WebSocket
                order_result = await self.websocket_client.place_market_order(
                    pair=self.test_symbol,
                    side="sell",
                    volume=self.order_amount_eth,
                    userref=int(time.time())  # Use timestamp as user reference
                )
                
                if order_result["success"]:
                    order_id = order_result["order_id"]
                    description = order_result["description"]
                    
                    print(f"   ✅ LIVE ORDER PLACED SUCCESSFULLY!")
                    print(f"   📋 Order ID: {order_id}")
                    print(f"   📋 Description: {description}")
                    
                    # Store order details for monitoring
                    self.placed_order_id = order_id
                    self.order_status = "submitted"
                    
                    # Monitor the order
                    await self._monitor_live_order(order_id)
                    
                else:
                    error_msg = order_result.get("error", "Unknown error")
                    print(f"   ❌ ORDER PLACEMENT FAILED: {error_msg}")
                    return False
                    
            except Exception as e:
                print(f"   ❌ ORDER PLACEMENT EXCEPTION: {e}")
                import traceback
                traceback.print_exc()
                print("   🔧 Falling back to simulation for safety...")
                await self._simulate_order_placement()'''
    
    new_content = content[:simulation_start] + real_order_code + content[line_end:]
    
    # Also need to add order monitoring method
    monitoring_method = '''
    
    async def _monitor_live_order(self, order_id: str, timeout: float = 60.0) -> None:
        """Monitor a live order until completion or timeout."""
        print(f"\n📊 MONITORING LIVE ORDER: {order_id}")
        print("-" * 50)
        
        import asyncio
        start_time = asyncio.get_event_loop().time()
        
        try:
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                # Check order status via OrderManager if available
                if self.websocket_client.order_manager:
                    # Look for order in OrderManager
                    all_orders = self.websocket_client.order_manager.get_all_orders()
                    for order in all_orders:
                        if hasattr(order, 'kraken_order_id') and order.kraken_order_id == order_id:
                            print(f"📊 Order Status: {order.current_state.value}")
                            print(f"📊 Fill: {order.fill_percentage:.1f}%")
                            
                            if order.is_terminal():
                                print(f"✅ Order completed: {order.current_state.value}")
                                self.order_status = order.current_state.value.lower()
                                return
                
                print("⏱️ Waiting for order completion...")
                await asyncio.sleep(5)  # Check every 5 seconds
                
        except Exception as e:
            print(f"⚠️ Order monitoring error: {e}")
        
        print(f"⏰ Order monitoring timeout after {timeout}s")'''
    
    # Add monitoring method before the last method
    if 'async def cleanup(self):' in new_content:
        cleanup_pos = new_content.find('async def cleanup(self):')
        method_start = new_content.rfind('\n    ', 0, cleanup_pos)
        if method_start == -1:
            method_start = cleanup_pos
        new_content = new_content[:method_start] + monitoring_method + '\n' + new_content[method_start:]
    else:
        new_content = new_content + monitoring_method
    
    try:
        with open(live_order_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ Updated live order placement script with real WebSocket order placement")
        return True
    except Exception as e:
        print(f"❌ Error writing live order placement script: {e}")
        return False


def main():
    """Main execution function."""
    print("🚀 IMPLEMENTING WEBSOCKET ORDER PLACEMENT")
    print("=" * 70)
    print()
    print("This implementation adds:")
    print("• place_market_order() method using WebSocket addOrder")
    print("• place_limit_order() method for limit orders")
    print("• cancel_order() method using WebSocket cancelOrder")
    print("• Real-time order response handling")
    print("• OrderManager integration for order tracking")
    print("• Live order monitoring capabilities")
    print()
    
    success1 = add_websocket_order_placement_methods()
    success2 = update_live_order_placement_script()
    
    if success1 and success2:
        print("\n🎉 SUCCESS: WebSocket Order Placement Implemented!")
        print("=" * 70)
        print("✅ WebSocket client now has real order placement methods")
        print("✅ Live order script uses real WebSocket orders")
        print("✅ Orders will be placed via Kraken's addOrder endpoint")
        print("✅ Real-time order monitoring and tracking enabled")
        print()
        print("🚀 NEXT STEPS:")
        print("1. Test with: python3 live_order_placement.py")
        print("2. Confirm real orders are placed (not simulated)")
        print("3. Monitor order execution in real-time")
        print("4. Verify OrderManager tracks the orders")
        print()
        print("⚠️ WARNING: This will now place REAL ORDERS with REAL MONEY!")
        return True
    else:
        print("\n❌ SOME IMPLEMENTATIONS FAILED")
        print("Check the errors above and fix manually if needed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
