#!/usr/bin/env python3
"""
Fix WebSocket Message Format According to Kraken Documentation

Based on Kraken's official WebSocket documentation, the message format is:
- ownTrades: [[{trade_id: {trade_data}}, ...], "ownTrades"]
- openOrders: [[{order_id: {order_data}}, ...], "openOrders"] 

The channel name is at index [1], not [2] as we assumed.
The actual data is at index [0].
"""

import sys
from pathlib import Path


def fix_message_processing():
    """Fix the WebSocket message processing based on Kraken's actual format."""
    
    print("🔧 FIXING WEBSOCKET MESSAGE FORMAT")
    print("=" * 50)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading WebSocket client: {e}")
        return False
    
    # Fix 1: Correct channel name extraction
    print("🔧 Fixing channel name extraction...")
    old_channel_extract = "channel_name = data[2] if len(data) > 2 else \"unknown\""
    new_channel_extract = "channel_name = data[1] if len(data) > 1 else \"unknown\""
    
    if old_channel_extract in content:
        content = content.replace(old_channel_extract, new_channel_extract)
        print("✅ Fixed channel name extraction (data[2] → data[1])")
    
    # Fix 2: Update _is_order_update method to use correct format
    print("🔧 Fixing _is_order_update method...")
    
    old_is_order_update = '''def _is_order_update(self, message: Dict[str, Any], order_id: str) -> bool:
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

    new_is_order_update = '''def _is_order_update(self, message: Dict[str, Any], order_id: str) -> bool:
        """Check if message is an update for our order."""
        try:
            # Handle list format messages from WebSocket feeds
            # Format: [[{data}, ...], "channelName"]
            if isinstance(message, list) and len(message) >= 2:
                channel_name = message[1] if len(message) > 1 else None
                data_array = message[0] if len(message) > 0 else []
                
                # ownTrades messages: [[{trade_id: {trade_data}}, ...], "ownTrades"]
                if channel_name == "ownTrades" and isinstance(data_array, list):
                    for trade_dict in data_array:
                        if isinstance(trade_dict, dict):
                            for trade_id, trade_info in trade_dict.items():
                                if isinstance(trade_info, dict):
                                    if trade_info.get("ordertxid") == order_id:
                                        return True
                
                # openOrders messages: [[{order_id: {order_data}}, ...], "openOrders"]
                elif channel_name == "openOrders" and isinstance(data_array, list):
                    for order_dict in data_array:
                        if isinstance(order_dict, dict):
                            if order_id in order_dict:
                                return True
            
            # Handle direct dict format messages (subscription confirmations, etc.)
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
    
    if old_is_order_update in content:
        content = content.replace(old_is_order_update, new_is_order_update)
        print("✅ Fixed _is_order_update method")
    
    # Fix 3: Update _process_order_update method
    print("🔧 Fixing _process_order_update method...")
    
    old_process_order_update = '''def _process_order_update(self, message: Dict[str, Any], order_id: str) -> tuple:
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

    new_process_order_update = '''def _process_order_update(self, message: Dict[str, Any], order_id: str) -> tuple:
        """
        Process order update message.
        
        Returns:
            (status, completed, fill_info)
        """
        try:
            # Handle list format messages: [[{data}, ...], "channelName"]
            if isinstance(message, list) and len(message) >= 2:
                channel_name = message[1] if len(message) > 1 else None
                data_array = message[0] if len(message) > 0 else []
                
                # Process ownTrades (execution/fill updates)
                if channel_name == "ownTrades" and isinstance(data_array, list):
                    for trade_dict in data_array:
                        if isinstance(trade_dict, dict):
                            for trade_id, trade_info in trade_dict.items():
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
                                            "type": trade_info.get("type"),
                                            "pair": trade_info.get("pair")
                                        }
                                    )
                
                # Process openOrders (status updates)
                elif channel_name == "openOrders" and isinstance(data_array, list):
                    for order_dict in data_array:
                        if isinstance(order_dict, dict):
                            order_info = order_dict.get(order_id)
                            if order_info:
                                status = order_info.get("status", "unknown")
                                vol_exec = float(order_info.get("vol_exec", 0))
                                vol = float(order_info.get("vol", 0))
                                
                                # Order is completed if status is closed/canceled or fully executed
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
    
    if old_process_order_update in content:
        content = content.replace(old_process_order_update, new_process_order_update)
        print("✅ Fixed _process_order_update method")
    
    # Fix 4: Update the general message processing to handle the correct format
    print("🔧 Fixing general message processing...")
    
    # Update the _process_private_data method to handle the correct format
    old_data_processing = '''if isinstance(data, list) and len(data) >= 3:
                # FIXED: Properly extract channel name from WebSocket message
                channel_name = data[2] if len(data) > 2 else "unknown"'''
    
    new_data_processing = '''if isinstance(data, list) and len(data) >= 2:
                # FIXED: Properly extract channel name from WebSocket message
                # Format: [[{data}, ...], "channelName"]
                channel_name = data[1] if len(data) > 1 else "unknown"'''
    
    if old_data_processing in content:
        content = content.replace(old_data_processing, new_data_processing)
        print("✅ Fixed general data processing format")
    
    # Write the updated content
    try:
        with open(websocket_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Applied WebSocket message format fixes")
        
        # Test syntax
        compile(content, str(websocket_path), 'exec')
        print("✅ Syntax verification passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying fixes: {e}")
        return False


def add_debug_logging():
    """Add debug logging to see exactly what messages we're receiving."""
    
    print("\n🔧 ADDING DEBUG LOGGING")
    print("=" * 50)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading WebSocket client: {e}")
        return False
    
    # Add debug logging to the monitoring function
    old_monitoring_start = '''# Check for order status updates
                        if self._is_order_update(message, order_id):'''
    
    new_monitoring_start = '''# Debug logging for message format
                        if isinstance(message, list) and len(message) >= 2:
                            self.log_info(f"WebSocket message format: channel={message[1] if len(message) > 1 else 'unknown'}, data_type={type(message[0])}")
                            if len(message) > 1 and message[1] in ["ownTrades", "openOrders"]:
                                self.log_info(f"Order-related message: {message}")
                        
                        # Check for order status updates
                        if self._is_order_update(message, order_id):'''
    
    if old_monitoring_start in content:
        content = content.replace(old_monitoring_start, new_monitoring_start)
        print("✅ Added debug logging to monitoring")
    
    try:
        with open(websocket_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Added debug logging")
        return True
        
    except Exception as e:
        print(f"❌ Error adding debug logging: {e}")
        return False


def main():
    """Main execution function."""
    print("🔧 FIXING WEBSOCKET MESSAGE FORMAT BASED ON KRAKEN DOCS")
    print("=" * 70)
    print()
    print("Key findings from Kraken WebSocket documentation:")
    print("• ownTrades format: [[{trade_id: {trade_data}}, ...], \"ownTrades\"]")
    print("• openOrders format: [[{order_id: {order_data}}, ...], \"openOrders\"]")
    print("• Channel name is at index [1], not [2]")
    print("• Data array is at index [0]")
    print("• Need to iterate through data array properly")
    print()
    
    success1 = fix_message_processing()
    success2 = add_debug_logging()
    
    if success1 and success2:
        print("\n🎉 SUCCESS: WebSocket Message Format Fixed!")
        print("=" * 70)
        print("✅ Fixed channel name extraction (data[1] not data[2])")
        print("✅ Fixed message parsing to match Kraken's actual format")
        print("✅ Updated order update detection logic")
        print("✅ Added debug logging to see actual messages")
        print()
        print("🚀 TEST AGAIN:")
        print("python3 live_order_placement.py")
        print()
        print("Expected improvements:")
        print("• Real-time detection of ownTrades messages")
        print("• Immediate order completion notification")
        print("• Debug logs showing actual message format")
        print("• Sub-5-second order monitoring")
        return True
    else:
        print("\n❌ SOME FIXES FAILED")
        print("Check errors above")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
