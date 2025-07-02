#!/usr/bin/env python3
"""
Fix Order Monitoring Issues

Fix the specific issues preventing real-time order monitoring:
1. OrderManager field error (kraken_order_id doesn't exist)
2. Message processing for order updates
3. Proper detection of order completion
"""

import sys
from pathlib import Path


def fix_ordermanager_integration():
    """Fix the OrderManager integration issues."""
    
    print("🔧 FIXING ORDERMANAGER INTEGRATION")
    print("=" * 50)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading WebSocket client: {e}")
        return False
    
    # Fix 1: Remove the invalid kraken_order_id field assignment
    print("🔧 Fixing kraken_order_id field assignment...")
    
    old_assignment = "order.kraken_order_id = order_id"
    new_assignment = """# Store Kraken order ID in order metadata instead
            order.metadata = order.metadata or {}
            order.metadata['kraken_order_id'] = order_id"""
    
    if old_assignment in content:
        content = content.replace(old_assignment, new_assignment)
        print("✅ Fixed kraken_order_id assignment")
    else:
        print("⚠️ kraken_order_id assignment not found")
    
    # Fix 2: Update the order monitoring to look for the right message format
    print("🔧 Fixing message processing...")
    
    # Find and replace the _is_order_update method
    old_method_start = content.find('def _is_order_update(self, message: Dict[str, Any], order_id: str) -> bool:')
    if old_method_start != -1:
        # Find the end of the method
        method_end = content.find('\n    def ', old_method_start + 1)
        if method_end == -1:
            method_end = content.find('\n    async def ', old_method_start + 1)
        if method_end == -1:
            method_end = content.find('\n\n    ', old_method_start + 1)
        
        if method_end != -1:
            # Replace the entire method
            new_method = '''def _is_order_update(self, message: Dict[str, Any], order_id: str) -> bool:
        """Check if message is an update for our order."""
        try:
            # Handle list format messages from WebSocket feeds
            if isinstance(message, list) and len(message) >= 3:
                channel_name = message[2] if len(message) > 2 else None
                
                # ownTrades messages
                if channel_name == "ownTrades":
                    trades_data = message[0]
                    for trade_id, trade_info in trades_data.items():
                        if isinstance(trade_info, dict):
                            if trade_info.get("ordertxid") == order_id:
                                return True
                
                # openOrders messages  
                elif channel_name == "openOrders":
                    orders_data = message[0]
                    if isinstance(orders_data, dict):
                        if order_id in orders_data:
                            return True
            
            # Handle direct dict format messages
            elif isinstance(message, dict):
                # Check if it's a subscription confirmation or order status
                if message.get("event") in ["subscriptionStatus", "addOrderStatus"]:
                    return False  # These aren't order updates
                
                # Check for order data in the message
                if "ordertxid" in message and message.get("ordertxid") == order_id:
                    return True
            
            return False
            
        except Exception as e:
            self.log_error("Error checking order update", error=e)
            return False'''
            
            content = content[:old_method_start] + new_method + content[method_end:]
            print("✅ Fixed _is_order_update method")
    
    # Fix 3: Update the _process_order_update method
    old_process_start = content.find('def _process_order_update(self, message: Dict[str, Any], order_id: str) -> tuple:')
    if old_process_start != -1:
        process_end = content.find('\n    def ', old_process_start + 1)
        if process_end == -1:
            process_end = content.find('\n    async def ', old_process_start + 1)
        if process_end == -1:
            process_end = content.find('\n\n    ', old_process_start + 1)
        
        if process_end != -1:
            new_process_method = '''def _process_order_update(self, message: Dict[str, Any], order_id: str) -> tuple:
        """
        Process order update message.
        
        Returns:
            (status, completed, fill_info)
        """
        try:
            # Process ownTrades (execution/fill updates)
            if isinstance(message, list) and len(message) >= 3 and message[2] == "ownTrades":
                trades_data = message[0]
                for trade_id, trade_info in trades_data.items():
                    if isinstance(trade_info, dict) and trade_info.get("ordertxid") == order_id:
                        return (
                            "filled",
                            True,
                            {
                                "trade_id": trade_id,
                                "price": trade_info.get("price"),
                                "vol": trade_info.get("vol"),
                                "cost": trade_info.get("cost"),
                                "fee": trade_info.get("fee"),
                                "time": trade_info.get("time"),
                                "type": trade_info.get("type")
                            }
                        )
            
            # Process openOrders (status updates)
            elif isinstance(message, list) and len(message) >= 3 and message[2] == "openOrders":
                orders_data = message[0]
                if isinstance(orders_data, dict):
                    order_info = orders_data.get(order_id)
                    if order_info:
                        status = order_info.get("status", "unknown")
                        vol_exec = float(order_info.get("vol_exec", 0))
                        vol = float(order_info.get("vol", 0))
                        
                        # Order is completed if status is closed or fully executed
                        completed = status in ["closed", "canceled", "expired"] or vol_exec >= vol
                        
                        return (
                            status,
                            completed,
                            {
                                "vol_exec": vol_exec,
                                "vol": vol,
                                "status": status,
                                "avg_price": order_info.get("avg_price"),
                                "cost": order_info.get("cost"),
                                "fee": order_info.get("fee")
                            }
                        )
            
            return ("unknown", False, {})
            
        except Exception as e:
            self.log_error("Error processing order update", error=e, order_id=order_id)
            return ("error", False, {"error": str(e)})'''
            
            content = content[:old_process_start] + new_process_method + content[process_end:]
            print("✅ Fixed _process_order_update method")
    
    # Fix 4: Improve the real-time monitoring loop
    old_monitor_start = content.find('async def monitor_order_realtime(self, order_id: str, timeout: float = 30.0) -> Dict[str, Any]:')
    if old_monitor_start != -1:
        monitor_end = content.find('\n    async def ', old_monitor_start + 1)
        if monitor_end == -1:
            monitor_end = content.find('\n    def ', old_monitor_start + 1)
        if monitor_end == -1:
            monitor_end = content.find('\n\n    ', old_monitor_start + 1)
        
        if monitor_end != -1:
            new_monitor_method = '''async def monitor_order_realtime(self, order_id: str, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Monitor order in real-time using WebSocket feeds.
        
        Args:
            order_id: Order ID to monitor
            timeout: Maximum time to wait for completion
            
        Returns:
            Order completion status
        """
        import asyncio
        
        print(f"📊 REAL-TIME ORDER MONITORING: {order_id}")
        print("-" * 50)
        
        start_time = asyncio.get_event_loop().time()
        order_completed = False
        order_status = "unknown"
        fill_info = {}
        
        try:
            # Ensure we're subscribed to order feeds
            await self.subscribe_to_order_feeds()
            
            # Give a moment for subscriptions to be confirmed
            await asyncio.sleep(0.5)
            
            # Monitor for order completion
            messages_checked = 0
            
            while (asyncio.get_event_loop().time() - start_time) < timeout and not order_completed:
                
                try:
                    # Check for messages with a shorter timeout for faster response
                    message = await asyncio.wait_for(
                        self.private_message_queue.get(), 
                        timeout=0.5
                    )
                    
                    messages_checked += 1
                    
                    if isinstance(message, (dict, list)):
                        # Log message type for debugging
                        if isinstance(message, list) and len(message) >= 3:
                            self.log_info(f"Processing message: {message[2] if len(message) > 2 else 'unknown'}")
                        
                        # Check for order status updates
                        if self._is_order_update(message, order_id):
                            order_status, order_completed, fill_info = self._process_order_update(
                                message, order_id
                            )
                            
                            print(f"📊 Order Update: {order_status}")
                            if fill_info:
                                print(f"📊 Fill Info: {fill_info}")
                            
                            if order_completed:
                                print(f"✅ Order completed: {order_status}")
                                break
                        else:
                            # Put message back for other processors
                            await self.private_message_queue.put(message)
                    
                except asyncio.TimeoutError:
                    # No messages - continue waiting
                    if messages_checked == 0:
                        print("⏱️ Waiting for order updates...")
                    continue
                    
                except Exception as e:
                    self.log_error("Error during real-time monitoring", error=e)
                    break
            
            if not order_completed:
                print(f"⏰ Monitoring timeout after {timeout}s (checked {messages_checked} messages)")
                order_status = "timeout"
            
            return {
                "completed": order_completed,
                "status": order_status,
                "fill_info": fill_info,
                "monitoring_time": asyncio.get_event_loop().time() - start_time,
                "messages_processed": messages_checked
            }
            
        except Exception as e:
            self.log_error("Real-time order monitoring failed", error=e)
            return {
                "completed": False,
                "status": "error",
                "error": str(e),
                "monitoring_time": asyncio.get_event_loop().time() - start_time
            }'''
            
            content = content[:old_monitor_start] + new_monitor_method + content[monitor_end:]
            print("✅ Fixed monitor_order_realtime method")
    
    try:
        with open(websocket_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Fixed WebSocket order monitoring")
        return True
    except Exception as e:
        print(f"❌ Error writing WebSocket client: {e}")
        return False


def improve_message_processing():
    """Improve the message processing to better handle order updates."""
    
    print("\n🔧 IMPROVING MESSAGE PROCESSING")
    print("=" * 50)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading WebSocket client: {e}")
        return False
    
    # Add better logging for unknown messages
    if 'log_websocket_event(' in content and '"unknown_private_data"' in content:
        # Find the unknown_private_data logging
        unknown_log_start = content.find('log_websocket_event(')
        if unknown_log_start != -1:
            # Find the full log statement
            log_end = content.find(')', unknown_log_start)
            if log_end != -1:
                # Add more detailed logging
                old_log = content[unknown_log_start:log_end + 1]
                new_log = '''log_websocket_event(
                        self.logger,
                        "unknown_private_data",
                        channel=channel_name,
                        data_type=type(data).__name__,
                        data_preview=str(data)[:200] if isinstance(data, (dict, list)) else None
                    )'''
                
                content = content.replace(old_log, new_log)
                print("✅ Improved unknown message logging")
    
    try:
        with open(websocket_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Improved message processing")
        return True
    except Exception as e:
        print(f"❌ Error writing WebSocket client: {e}")
        return False


def main():
    """Main execution function."""
    print("🔧 FIXING ORDER MONITORING ISSUES")
    print("=" * 60)
    print()
    print("Issues identified:")
    print("• OrderManager field error (kraken_order_id)")
    print("• Message processing for order updates")
    print("• Real-time monitoring timeout")
    print("• Unknown private data handling")
    print()
    
    success1 = fix_ordermanager_integration()
    success2 = improve_message_processing()
    
    if success1 and success2:
        print("\n🎉 SUCCESS: Order Monitoring Issues Fixed!")
        print("=" * 60)
        print("✅ Fixed OrderManager integration")
        print("✅ Improved message processing for order updates")
        print("✅ Enhanced real-time monitoring logic")
        print("✅ Better error handling and logging")
        print()
        print("🚀 TEST AGAIN:")
        print("python3 live_order_placement.py")
        print()
        print("Expected improvements:")
        print("• No more kraken_order_id field errors")
        print("• Better processing of ownTrades/openOrders")
        print("• Faster order completion detection")
        print("• More detailed monitoring logs")
        return True
    else:
        print("\n❌ SOME FIXES FAILED")
        print("Check errors above")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
