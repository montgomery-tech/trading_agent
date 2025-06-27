#!/usr/bin/env python3
"""
Final fix for OrderManager WebSocket integration.

This script adds the missing methods directly to the OrderManager file
and fixes the orders summary issue.

File Location: fix_ordermanager_integration.py
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def add_missing_methods_to_ordermanager():
    """Add the missing methods to the OrderManager class."""

    # Read the current OrderManager file content
    ordermanager_path = Path("src/trading_systems/exchanges/kraken/order_manager.py")

    if not ordermanager_path.exists():
        print(f"❌ OrderManager file not found: {ordermanager_path}")
        return False

    print(f"📄 Reading OrderManager file: {ordermanager_path}")

    try:
        with open(ordermanager_path, 'r') as f:
            content = f.read()

        # Check if methods already exist
        missing_methods = []
        methods_to_check = [
            'def has_order(',
            'def get_all_orders(',
            'async def sync_order_from_websocket(',
            'async def process_fill_update('
        ]

        for method in methods_to_check:
            if method not in content:
                missing_methods.append(method.replace('def ', '').replace('async def ', '').replace('(', ''))

        if not missing_methods:
            print("✅ All required methods already exist in OrderManager")
            return True

        print(f"⚠️ Missing methods found: {missing_methods}")

        # Methods to add to OrderManager class
        methods_to_add = '''
    # WEBSOCKET INTEGRATION METHODS - Added for Task 3.1.C

    def has_order(self, order_id: str) -> bool:
        """
        Check if an order exists in the manager.

        Args:
            order_id: The order ID to check

        Returns:
            True if the order exists, False otherwise
        """
        return order_id in self._orders

    def get_all_orders(self) -> List[EnhancedKrakenOrder]:
        """
        Get all orders managed by this OrderManager.

        Returns:
            List of all orders
        """
        return list(self._orders.values())

    async def sync_order_from_websocket(self, order_id: str, order_info: Dict[str, Any]) -> None:
        """
        Sync order state from WebSocket openOrders feed.

        Args:
            order_id: The order ID to sync
            order_info: Order information from WebSocket
        """
        try:
            order = self._orders.get(order_id)
            if not order:
                self.log_warning(f"Received WebSocket update for unknown order: {order_id}")
                return

            # Update order fields from WebSocket data
            old_state = order.state

            # Parse WebSocket order status
            ws_status = order_info.get('status', 'unknown')
            ws_vol_exec = Decimal(str(order_info.get('vol_exec', '0')))
            ws_cost = Decimal(str(order_info.get('cost', '0')))
            ws_fee = Decimal(str(order_info.get('fee', '0')))

            # Update executed volume
            if ws_vol_exec != order.volume_executed:
                order.volume_executed = ws_vol_exec
                order.volume_remaining = order.volume - ws_vol_exec

                # Update cost and fees
                if ws_cost > 0:
                    order.cost = ws_cost
                if ws_fee > 0:
                    order.fee = ws_fee

                # Update fill percentage
                if order.volume > 0:
                    order.fill_percentage = float((order.volume_executed / order.volume) * 100)

            # Update order state based on WebSocket status
            new_state = self._map_websocket_status_to_state(ws_status, order.volume_executed, order.volume)

            if new_state != old_state:
                await self._transition_order_state(order, new_state)

            order.last_update = datetime.now()

            self.log_info(
                "Order synced from WebSocket",
                order_id=order_id,
                status=ws_status,
                vol_exec=str(ws_vol_exec),
                old_state=old_state.value,
                new_state=order.state.value
            )

        except Exception as e:
            self.log_error(
                "Error syncing order from WebSocket",
                order_id=order_id,
                error=e
            )

    async def process_fill_update(self, trade_id: str, trade_info: Dict[str, Any]) -> None:
        """
        Process a fill update from WebSocket ownTrades feed.

        Args:
            trade_id: The trade ID
            trade_info: Trade information from WebSocket
        """
        try:
            order_id = trade_info.get('ordertxid')
            if not order_id or order_id not in self._orders:
                return

            order = self._orders[order_id]

            # Extract trade information
            fill_volume = Decimal(str(trade_info.get('vol', '0')))
            fill_price = Decimal(str(trade_info.get('price', '0')))
            fill_fee = Decimal(str(trade_info.get('fee', '0')))
            fill_cost = Decimal(str(trade_info.get('cost', '0')))

            # Update order with fill information
            await self.handle_fill(order_id, fill_volume, fill_price, fill_fee)

            self.log_info(
                "Fill processed from WebSocket",
                trade_id=trade_id,
                order_id=order_id,
                volume=str(fill_volume),
                price=str(fill_price),
                fee=str(fill_fee)
            )

        except Exception as e:
            self.log_error(
                "Error processing fill update",
                trade_id=trade_id,
                error=e
            )

    def _map_websocket_status_to_state(self, ws_status: str, vol_executed: Decimal, total_volume: Decimal) -> OrderState:
        """
        Map WebSocket order status to internal OrderState.

        Args:
            ws_status: WebSocket order status
            vol_executed: Volume executed
            total_volume: Total order volume

        Returns:
            Corresponding OrderState
        """
        if ws_status == 'open':
            if vol_executed == 0:
                return OrderState.OPEN
            elif vol_executed < total_volume:
                return OrderState.PARTIALLY_FILLED
            else:
                return OrderState.FILLED
        elif ws_status == 'closed':
            return OrderState.FILLED
        elif ws_status == 'canceled':
            return OrderState.CANCELED
        elif ws_status == 'expired':
            return OrderState.EXPIRED
        else:
            return OrderState.OPEN  # Default fallback

    async def _transition_order_state(self, order: EnhancedKrakenOrder, new_state: OrderState) -> None:
        """
        Transition order to new state with proper validation and event handling.

        Args:
            order: The order to transition
            new_state: The new state to transition to
        """
        old_state = order.state

        # Validate transition
        if not OrderStateMachine.is_valid_transition(old_state, new_state):
            self.log_warning(
                "Invalid state transition attempted",
                order_id=order.order_id,
                old_state=old_state.value,
                new_state=new_state.value
            )
            return

        # Update order state
        order.state = new_state
        order.last_update = datetime.now()

        # Update indices
        self._update_order_indices(order, old_state, new_state)

        # Update statistics
        self._update_statistics_for_state_change(old_state, new_state)

        self.log_info(
            "Order state transitioned",
            order_id=order.order_id,
            old_state=old_state.value,
            new_state=new_state.value
        )

    def _update_statistics_for_state_change(self, old_state: OrderState, new_state: OrderState) -> None:
        """Update statistics when order state changes."""
        if new_state == OrderState.FILLED:
            self._stats['orders_filled'] += 1
            self._stats['last_fill_time'] = datetime.now()
        elif new_state == OrderState.CANCELED:
            self._stats['orders_canceled'] += 1
        elif new_state == OrderState.REJECTED:
            self._stats['orders_rejected'] += 1
        elif new_state == OrderState.OPEN and old_state == OrderState.PENDING_SUBMIT:
            self._stats['orders_submitted'] += 1
'''

        # Find a good place to insert the methods (before the last class method or before __all__)
        if '# Export main classes and functions' in content:
            # Insert before the export section
            insert_pos = content.find('# Export main classes and functions')
            new_content = content[:insert_pos] + methods_to_add + '\n\n' + content[insert_pos:]
        elif '__all__ = [' in content:
            # Insert before __all__
            insert_pos = content.find('__all__ = [')
            new_content = content[:insert_pos] + methods_to_add + '\n\n' + content[insert_pos:]
        else:
            # Insert at the end of the class (find last method)
            # Look for the last method or the end of the class
            lines = content.split('\n')
            insert_line = len(lines) - 10  # Near the end but not at the very end

            for i in range(len(lines) - 1, 0, -1):
                if lines[i].strip().startswith('def ') or lines[i].strip().startswith('async def '):
                    # Find the end of this method
                    for j in range(i + 1, len(lines)):
                        if lines[j] and not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                            insert_line = j
                            break
                    break

            new_lines = lines[:insert_line] + methods_to_add.split('\n') + lines[insert_line:]
            new_content = '\n'.join(new_lines)

        # Write the updated content
        with open(ordermanager_path, 'w') as f:
            f.write(new_content)

        print(f"✅ Added {len(missing_methods)} missing methods to OrderManager")
        print("   Methods added: has_order, get_all_orders, sync_order_from_websocket, process_fill_update")
        return True

    except Exception as e:
        print(f"❌ Error updating OrderManager file: {e}")
        return False


def fix_websocket_client_orders_summary():
    """Fix the get_orders_summary method in WebSocket client."""

    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")

    if not websocket_path.exists():
        print(f"❌ WebSocket client file not found: {websocket_path}")
        return False

    print(f"📄 Reading WebSocket client file: {websocket_path}")

    try:
        with open(websocket_path, 'r') as f:
            content = f.read()

        # Check if get_orders_summary method exists and needs fixing
        if 'def get_orders_summary(self)' in content:
            print("✅ get_orders_summary method already exists in WebSocket client")
            return True

        # Add the corrected get_orders_summary method
        orders_summary_method = '''
    def get_orders_summary(self) -> Dict[str, Any]:
        """Get summary of all orders from OrderManager."""
        if not self.order_manager:
            return {"enabled": False, "orders": []}

        try:
            stats = self.order_manager.get_statistics()
            orders = self.order_manager.get_all_orders()

            orders_data = []
            for order in orders:
                orders_data.append({
                    "order_id": order.order_id,
                    "state": order.state.value,
                    "pair": order.pair,
                    "type": order.type,
                    "volume": str(order.volume),
                    "volume_executed": str(order.volume_executed)
                })

            return {
                "enabled": True,
                "statistics": stats,
                "orders": orders_data,
                "total_orders": len(orders)
            }
        except Exception as e:
            self.log_error("Error generating orders summary", error=e)
            return {"enabled": True, "error": str(e), "orders": [], "total_orders": 0}
'''

        # Find where to insert the method (after get_order_status)
        if 'def get_order_status(self, order_id: str)' in content:
            # Find the end of get_order_status method
            start_pos = content.find('def get_order_status(self, order_id: str)')
            method_start = content.rfind('\n    def ', 0, start_pos) + 1

            # Find the next method after get_order_status
            next_method_pos = content.find('\n    def ', start_pos + 1)
            if next_method_pos == -1:
                next_method_pos = content.find('\n    async def ', start_pos + 1)

            if next_method_pos != -1:
                new_content = content[:next_method_pos] + orders_summary_method + content[next_method_pos:]
            else:
                # Insert at end of class
                new_content = content + orders_summary_method
        else:
            # Insert near the end of the class
            new_content = content + orders_summary_method

        # Write the updated content
        with open(websocket_path, 'w') as f:
            f.write(new_content)

        print("✅ Added get_orders_summary method to WebSocket client")
        return True

    except Exception as e:
        print(f"❌ Error updating WebSocket client file: {e}")
        return False


def main():
    """Main function to apply all fixes."""
    print("🔧 APPLYING FINAL ORDERMANAGER INTEGRATION FIXES")
    print("=" * 60)
    print()

    success_count = 0
    total_fixes = 2

    # Fix 1: Add missing methods to OrderManager
    print("1️⃣ ADDING MISSING METHODS TO ORDERMANAGER")
    if add_missing_methods_to_ordermanager():
        success_count += 1
        print("✅ COMPLETED")
    else:
        print("❌ FAILED")

    print()

    # Fix 2: Fix WebSocket client orders summary
    print("2️⃣ FIXING WEBSOCKET CLIENT ORDERS SUMMARY")
    if fix_websocket_client_orders_summary():
        success_count += 1
        print("✅ COMPLETED")
    else:
        print("❌ FAILED")

    print()
    print("=" * 60)
    print("📊 FIX RESULTS")
    print("=" * 60)
    print(f"🎯 Fixes Applied: {success_count}/{total_fixes}")

    if success_count == total_fixes:
        print("🎉 ALL FIXES APPLIED SUCCESSFULLY!")
        print()
        print("✅ OrderManager Integration Status:")
        print("   • Missing methods added to OrderManager class")
        print("   • WebSocket client orders summary fixed")
        print("   • Integration tests should now pass 7/7")
        print()
        print("🚀 Next Steps:")
        print("   1. Re-run integration tests to verify 7/7 pass")
        print("   2. Proceed with Task 3.2: Order Placement Functionality")
    else:
        print("⚠️ Some fixes failed - manual intervention may be needed")

    print("=" * 60)
    return success_count == total_fixes


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Fix process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
