#!/usr/bin/env python3
"""
Task 3.4.B.1: Enhanced Order Request Models Test Suite

This comprehensive test suite validates all advanced order types and functionality
implemented in Task 3.4.B.1.

Tests:
1. Basic order types (market, limit)
2. Stop-loss and take-profit orders (fixed)
3. Conditional orders (new)
4. OCO orders (new)
5. Iceberg orders (new)
6. Validation and error handling
7. Factory functions
8. API serialization

File: test_task_3_4_b_1_order_models.py
Run: python3 test_task_3_4_b_1_order_models.py
"""

import sys
import time
from pathlib import Path
from decimal import Decimal

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.order_requests import (
        # Basic order types
        MarketOrderRequest,
        LimitOrderRequest,

        # Advanced order types
        StopLossOrderRequest,
        TakeProfitOrderRequest,
        StopLossLimitOrderRequest,
        ConditionalOrderRequest,
        OCOOrderRequest,
        IcebergOrderRequest,

        # Enums
        TimeInForce,
        OrderFlags,
        TriggerType,
        ConditionOperator,
        OCOType,

        # Factory functions
        create_market_order,
        create_limit_order,
        create_stop_loss_order,
        create_take_profit_order,
        create_conditional_order,
        create_oco_order,
        create_iceberg_order,

        # Validation
        validate_order_request,
        validate_oco_order,

        # Response models
        OrderPlacementResponse,
        OCOPlacementResponse,
        OrderValidationResult,

        # Utilities
        serialize_order_for_api,
        estimate_order_fees,
        OrderRequestFactory
    )
    from trading_systems.exchanges.kraken.account_models import OrderSide, OrderType, OrderStatus
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\n🔧 Make sure to run: python3 implement_task_3_4_b_1_order_models.py first")
    sys.exit(1)


class Task_3_4_B_1_TestSuite:
    """Comprehensive test suite for Task 3.4.B.1 implementation."""

    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()

    def run_full_test_suite(self):
        """Run the complete enhanced order models test suite."""
        print("🧪 TASK 3.4.B.1: ENHANCED ORDER MODELS - TEST SUITE")
        print("=" * 70)
        print("Testing all advanced order types and functionality")
        print("=" * 70)

        try:
            # Test Categories
            self._test_1_basic_order_types()
            self._test_2_fixed_stop_orders()
            self._test_3_conditional_orders()
            self._test_4_oco_orders()
            self._test_5_iceberg_orders()
            self._test_6_validation_framework()
            self._test_7_factory_functions()
            self._test_8_api_serialization()
            self._test_9_response_models()
            self._test_10_advanced_features()

        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self._generate_comprehensive_report()

    def _test_1_basic_order_types(self):
        """Test 1: Basic order types (market, limit)."""
        print("\n1️⃣ BASIC ORDER TYPES")
        print("-" * 50)

        try:
            # Test market order
            market_order = MarketOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("1.0")
            )

            assert market_order.order_type == OrderType.MARKET
            assert market_order.pair == "XBTUSD"
            assert market_order.side == OrderSide.BUY
            print("  ✅ Market order created successfully")

            # Test limit order
            limit_order = LimitOrderRequest(
                pair="ETHUSD",
                side=OrderSide.SELL,
                volume=Decimal("2.0"),
                price=Decimal("2500.00")
            )

            assert limit_order.order_type == OrderType.LIMIT
            assert limit_order.price == Decimal("2500.00")
            print("  ✅ Limit order created successfully")

            self.test_results['basic_order_types'] = True
            print("✅ Basic order types: PASSED")

        except Exception as e:
            print(f"  ❌ Basic order types failed: {e}")
            self.test_results['basic_order_types'] = False

    def _test_2_fixed_stop_orders(self):
        """Test 2: Fixed stop-loss and take-profit orders."""
        print("\n2️⃣ FIXED STOP ORDERS")
        print("-" * 50)

        try:
            # Test stop-loss order with correct field mapping
            stop_loss = StopLossOrderRequest(
                pair="XBTUSD",
                side=OrderSide.SELL,
                volume=Decimal("1.0"),
                price=Decimal("45000.00")  # Using 'price' field
            )

            assert stop_loss.order_type == OrderType.STOP_LOSS
            assert stop_loss.price == Decimal("45000.00")
            assert stop_loss.trigger == TriggerType.LAST
            print("  ✅ Stop-loss order created with correct field mapping")

            # Test take-profit order
            take_profit = TakeProfitOrderRequest(
                pair="ETHUSD",
                side=OrderSide.SELL,
                volume=Decimal("2.0"),
                price=Decimal("3500.00")  # Using 'price' field
            )

            assert take_profit.order_type == OrderType.TAKE_PROFIT
            assert take_profit.price == Decimal("3500.00")
            print("  ✅ Take-profit order created with correct field mapping")

            # Test stop-loss-limit order
            stop_loss_limit = StopLossLimitOrderRequest(
                pair="XBTUSD",
                side=OrderSide.SELL,
                volume=Decimal("1.0"),
                price=Decimal("48000.00"),  # Stop price
                price2=Decimal("47500.00")  # Limit price
            )

            assert stop_loss_limit.order_type == OrderType.STOP_LOSS_LIMIT
            assert stop_loss_limit.price == Decimal("48000.00")
            assert stop_loss_limit.price2 == Decimal("47500.00")
            print("  ✅ Stop-loss-limit order created successfully")

            self.test_results['fixed_stop_orders'] = True
            print("✅ Fixed stop orders: PASSED")

        except Exception as e:
            print(f"  ❌ Fixed stop orders failed: {e}")
            self.test_results['fixed_stop_orders'] = False

    def _test_3_conditional_orders(self):
        """Test 3: New conditional orders."""
        print("\n3️⃣ CONDITIONAL ORDERS")
        print("-" * 50)

        try:
            # Test conditional order creation
            conditional_order = ConditionalOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("1.0"),
                price=Decimal("49000.00"),
                condition_price=Decimal("50000.00"),
                condition_operator=ConditionOperator.GREATER_THAN,
                condition_trigger=TriggerType.LAST
            )

            assert conditional_order.condition_price == Decimal("50000.00")
            assert conditional_order.condition_operator == ConditionOperator.GREATER_THAN
            print("  ✅ Conditional order created successfully")

            # Test condition evaluation
            condition_met = conditional_order.evaluate_condition(Decimal("50001.00"))
            assert condition_met == True
            print("  ✅ Condition evaluation works correctly (True case)")

            condition_not_met = conditional_order.evaluate_condition(Decimal("49999.00"))
            assert condition_not_met == False
            print("  ✅ Condition evaluation works correctly (False case)")

            self.test_results['conditional_orders'] = True
            print("✅ Conditional orders: PASSED")

        except Exception as e:
            print(f"  ❌ Conditional orders failed: {e}")
            self.test_results['conditional_orders'] = False

    def _test_4_oco_orders(self):
        """Test 4: New OCO (One-Cancels-Other) orders."""
        print("\n4️⃣ OCO ORDERS")
        print("-" * 50)

        try:
            # Create individual orders for OCO
            take_profit = TakeProfitOrderRequest(
                pair="XBTUSD",
                side=OrderSide.SELL,
                volume=Decimal("1.0"),
                price=Decimal("55000.00")
            )

            stop_loss = StopLossOrderRequest(
                pair="XBTUSD",
                side=OrderSide.SELL,
                volume=Decimal("1.0"),
                price=Decimal("45000.00")
            )

            # Test OCO order creation
            oco_order = OCOOrderRequest(
                primary_order=take_profit,
                secondary_order=stop_loss,
                oco_type=OCOType.TAKE_PROFIT_STOP_LOSS
            )

            assert oco_order.pair == "XBTUSD"
            assert oco_order.volume == Decimal("1.0")
            assert oco_order.oco_type == OCOType.TAKE_PROFIT_STOP_LOSS
            print("  ✅ OCO order created successfully")

            # Test validation
            oco_validation = validate_oco_order(oco_order)
            assert oco_validation.is_valid == True
            print("  ✅ OCO order validation passed")

            self.test_results['oco_orders'] = True
            print("✅ OCO orders: PASSED")

        except Exception as e:
            print(f"  ❌ OCO orders failed: {e}")
            self.test_results['oco_orders'] = False

    def _test_5_iceberg_orders(self):
        """Test 5: New iceberg orders."""
        print("\n5️⃣ ICEBERG ORDERS")
        print("-" * 50)

        try:
            # Test iceberg order creation
            iceberg_order = IcebergOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("10.0"),
                price=Decimal("50000.00"),
                display_volume=Decimal("1.0")
            )

            assert iceberg_order.volume == Decimal("10.0")
            assert iceberg_order.display_volume == Decimal("1.0")
            assert iceberg_order.refresh_threshold == Decimal("0.1")  # Default 10%
            print("  ✅ Iceberg order created successfully")

            # Test display volume calculation
            next_display = iceberg_order.calculate_next_display_volume(Decimal("5.5"))
            assert next_display == Decimal("1.0")  # Should return display_volume
            print("  ✅ Display volume calculation works")

            # Test with remaining < display
            next_display_small = iceberg_order.calculate_next_display_volume(Decimal("0.5"))
            assert next_display_small == Decimal("0.5")  # Should return remaining
            print("  ✅ Display volume calculation for small remaining works")

            self.test_results['iceberg_orders'] = True
            print("✅ Iceberg orders: PASSED")

        except Exception as e:
            print(f"  ❌ Iceberg orders failed: {e}")
            self.test_results['iceberg_orders'] = False

    def _test_6_validation_framework(self):
        """Test 6: Enhanced validation framework."""
        print("\n6️⃣ VALIDATION FRAMEWORK")
        print("-" * 50)

        try:
            # Test valid order validation
            valid_order = LimitOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("1.0"),
                price=Decimal("50000.00")
            )

            validation_result = validate_order_request(valid_order)
            assert validation_result.is_valid == True
            print("  ✅ Valid order passes validation")

            # Test iceberg validation with warnings
            iceberg_large_display = IcebergOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("2.0"),
                price=Decimal("50000.00"),
                display_volume=Decimal("1.5")  # 75% display ratio
            )

            iceberg_validation = validate_order_request(iceberg_large_display)
            assert iceberg_validation.is_valid == True
            assert len(iceberg_validation.warnings) > 0  # Should have warnings
            print("  ✅ Iceberg validation with warnings works")

            self.test_results['validation_framework'] = True
            print("✅ Validation framework: PASSED")

        except Exception as e:
            print(f"  ❌ Validation framework failed: {e}")
            self.test_results['validation_framework'] = False

    def _test_7_factory_functions(self):
        """Test 7: Enhanced factory functions."""
        print("\n7️⃣ FACTORY FUNCTIONS")
        print("-" * 50)

        try:
            # Test basic factory functions
            market = create_market_order("XBTUSD", OrderSide.BUY, "1.0")
            assert isinstance(market, MarketOrderRequest)
            print("  ✅ Market order factory works")

            limit = create_limit_order("XBTUSD", OrderSide.BUY, "1.0", "50000.00")
            assert isinstance(limit, LimitOrderRequest)
            print("  ✅ Limit order factory works")

            # Test advanced factory functions
            stop_loss = create_stop_loss_order("XBTUSD", OrderSide.SELL, "1.0", "45000.00")
            assert isinstance(stop_loss, StopLossOrderRequest)
            assert stop_loss.price == Decimal("45000.00")
            print("  ✅ Stop-loss order factory works")

            take_profit = create_take_profit_order("XBTUSD", OrderSide.SELL, "1.0", "55000.00")
            assert isinstance(take_profit, TakeProfitOrderRequest)
            print("  ✅ Take-profit order factory works")

            conditional = create_conditional_order(
                "XBTUSD", OrderSide.BUY, "1.0", "49000.00",
                "50000.00", ConditionOperator.GREATER_THAN
            )
            assert isinstance(conditional, ConditionalOrderRequest)
            print("  ✅ Conditional order factory works")

            oco = create_oco_order("XBTUSD", OrderSide.BUY, "1.0", "55000.00", "45000.00")
            assert isinstance(oco, OCOOrderRequest)
            print("  ✅ OCO order factory works")

            iceberg = create_iceberg_order("XBTUSD", OrderSide.BUY, "10.0", "50000.00", "1.0")
            assert isinstance(iceberg, IcebergOrderRequest)
            print("  ✅ Iceberg order factory works")

            self.test_results['factory_functions'] = True
            print("✅ Factory functions: PASSED")

        except Exception as e:
            print(f"  ❌ Factory functions failed: {e}")
            self.test_results['factory_functions'] = False

    def _test_8_api_serialization(self):
        """Test 8: API serialization functionality."""
        print("\n8️⃣ API SERIALIZATION")
        print("-" * 50)

        try:
            # Test basic order serialization
            limit_order = create_limit_order("XBTUSD", OrderSide.BUY, "1.0", "50000.00")
            api_data = serialize_order_for_api(limit_order)

            expected_fields = {"pair", "type", "ordertype", "volume", "price"}
            assert all(field in api_data for field in expected_fields)
            assert api_data["pair"] == "XBTUSD"
            assert api_data["type"] == "buy"
            assert api_data["ordertype"] == "limit"
            print("  ✅ Basic order serialization works")

            # Test advanced order serialization
            stop_loss = create_stop_loss_order("XBTUSD", OrderSide.SELL, "1.0", "45000.00")
            stop_api_data = serialize_order_for_api(stop_loss)

            assert stop_api_data["ordertype"] == "stop-loss"
            assert stop_api_data["price"] == "45000.00"
            print("  ✅ Stop-loss order serialization works")

            # Test fee estimation
            estimated_fees = estimate_order_fees(limit_order)
            assert estimated_fees > Decimal("0")
            print("  ✅ Fee estimation works")

            self.test_results['api_serialization'] = True
            print("✅ API serialization: PASSED")

        except Exception as e:
            print(f"  ❌ API serialization failed: {e}")
            self.test_results['api_serialization'] = False

    def _test_9_response_models(self):
        """Test 9: Response models functionality."""
        print("\n9️⃣ RESPONSE MODELS")
        print("-" * 50)

        try:
            # Test OrderPlacementResponse
            from trading_systems.exchanges.kraken.order_requests import OrderDescription

            order_desc = OrderDescription(
                pair="XBTUSD",
                type="buy",
                ordertype="limit",
                price="50000.00",
                order="buy 1.00000000 XBTUSD @ limit 50000.00"
            )

            placement_response = OrderPlacementResponse(
                txid=["ORDER123"],
                descr=order_desc
            )

            assert placement_response.order_id == "ORDER123"
            assert placement_response.is_success == True
            print("  ✅ OrderPlacementResponse works")

            # Test OCOPlacementResponse
            primary_response = OrderPlacementResponse(
                txid=["ORDER456"],
                descr=order_desc
            )

            secondary_response = OrderPlacementResponse(
                txid=["ORDER789"],
                descr=order_desc
            )

            oco_response = OCOPlacementResponse(
                primary_response=primary_response,
                secondary_response=secondary_response,
                oco_group_id="OCO123"
            )

            assert oco_response.is_success == True
            assert len(oco_response.order_ids) == 2
            print("  ✅ OCOPlacementResponse works")

            self.test_results['response_models'] = True
            print("✅ Response models: PASSED")

        except Exception as e:
            print(f"  ❌ Response models failed: {e}")
            self.test_results['response_models'] = False

    def _test_10_advanced_features(self):
        """Test 10: Advanced features and factory patterns."""
        print("\n🔟 ADVANCED FEATURES")
        print("-" * 50)

        try:
            # Test bracket order creation
            bracket_orders = OrderRequestFactory.create_bracket_order(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume="1.0",
                entry_price="50000.00",
                take_profit_price="55000.00",
                stop_loss_price="45000.00"
            )

            assert "entry_order" in bracket_orders
            assert "exit_oco" in bracket_orders
            assert isinstance(bracket_orders["entry_order"], LimitOrderRequest)
            assert isinstance(bracket_orders["exit_oco"], OCOOrderRequest)
            print("  ✅ Bracket order factory works")

            # Test scaled iceberg orders
            scaled_icebergs = OrderRequestFactory.create_scaled_iceberg_orders(
                pair="XBTUSD",
                side=OrderSide.BUY,
                total_volume="10.0",
                price_levels=["49000.00", "49500.00", "50000.00"],
                display_volume="1.0"
            )

            assert len(scaled_icebergs) == 3
            assert all(isinstance(order, IcebergOrderRequest) for order in scaled_icebergs)
            assert all(order.volume == Decimal("3.333333333333333333333333333") for order in scaled_icebergs)
            print("  ✅ Scaled iceberg orders factory works")

            self.test_results['advanced_features'] = True
            print("✅ Advanced features: PASSED")

        except Exception as e:
            print(f"  ❌ Advanced features failed: {e}")
            self.test_results['advanced_features'] = False

    def _generate_comprehensive_report(self):
        """Generate comprehensive test report."""
        print("\n" + "=" * 70)
        print("📊 TASK 3.4.B.1 IMPLEMENTATION REPORT")
        print("=" * 70)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        failed_tests = total_tests - passed_tests

        print(f"🎯 Tests Executed: {total_tests}")
        print(f"✅ Tests Passed: {passed_tests}")
        print(f"❌ Tests Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")

        execution_time = time.time() - self.start_time
        print(f"⏱️ Execution Time: {execution_time:.2f} seconds")

        print("\n📋 TEST BREAKDOWN:")
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {status} - {test_name.replace('_', ' ').title()}")

        if passed_tests == total_tests:
            print("\n🎉 TASK 3.4.B.1: ENHANCED ORDER MODELS - COMPLETE!")
            print("\n✅ All Advanced Order Types Implemented:")
            print("   • Fixed StopLossOrderRequest and TakeProfitOrderRequest")
            print("   • New ConditionalOrderRequest with trigger evaluation")
            print("   • New OCOOrderRequest (One-Cancels-Other)")
            print("   • New IcebergOrderRequest with smart display logic")
            print("   • Enhanced validation framework")
            print("   • Comprehensive factory functions")
            print("   • API serialization utilities")
            print("   • Advanced response models")
            print("   • Factory patterns for complex order strategies")
            print("\n🎯 Ready for Task 3.4.B.2: Advanced Order Processing Logic")

        else:
            print("\n⚠️  SOME TESTS FAILED - Review and fix issues before proceeding")
            print("\n🔧 Failed test areas:")
            for test_name, result in self.test_results.items():
                if not result:
                    print(f"   • {test_name.replace('_', ' ').title()}")

        print("=" * 70)


def main():
    """Main execution function."""
    print("🚀 TASK 3.4.B.1: ENHANCED ORDER REQUEST MODELS")
    print("=" * 70)
    print("Testing complete implementation of advanced order types")
    print("=" * 70)

    # Run test suite
    test_suite = Task_3_4_B_1_TestSuite()
    test_suite.run_full_test_suite()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
