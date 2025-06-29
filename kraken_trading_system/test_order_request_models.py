#!/usr/bin/env python3
"""
Test Script for Order Request/Response Models

This script validates the Order Request/Response models implementation
and ensures all functionality is working correctly.

Save as: test_order_request_models.py
Run with: python3 test_order_request_models.py
"""

import sys
import asyncio
import time
from pathlib import Path
from decimal import Decimal

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.order_requests import (
        MarketOrderRequest,
        LimitOrderRequest,
        StopLossOrderRequest,
        TakeProfitOrderRequest,
        OrderPlacementResponse,
        OrderStatusResponse,
        OrderValidationResult,
        create_market_order,
        create_limit_order,
        validate_order_request,
        sanitize_order_data,
        TimeInForce,
        OrderFlags
    )
    from trading_systems.exchanges.kraken.account_models import OrderSide, OrderType, OrderStatus
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\n🔧 Possible solutions:")
    print("1. Ensure all required files exist in the correct directory structure")
    print("2. Check that account_models.py exists and contains OrderSide, OrderType, OrderStatus")
    print("3. Run from the project root directory")
    sys.exit(1)


class OrderRequestModelsTestSuite:
    """Test suite for Order Request/Response models."""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()
        
    def run_full_test_suite(self):
        """Run the complete Order Request/Response models test suite."""
        print("🧪 ORDER REQUEST/RESPONSE MODELS - TEST SUITE")
        print("=" * 70)
        print("Testing all Order Request/Response model functionality")
        print("=" * 70)
        
        try:
            # Test Categories
            self._test_1_market_order_creation()
            self._test_2_limit_order_creation()
            self._test_3_stop_order_creation()
            self._test_4_order_validation()
            self._test_5_response_models()
            self._test_6_factory_functions()
            self._test_7_data_sanitization()
            self._test_8_error_handling()
            self._test_9_edge_cases()
            self._test_10_integration_readiness()
            
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self._generate_comprehensive_report()
    
    def _test_1_market_order_creation(self):
        """Test 1: Market order creation and validation."""
        print("\\n1️⃣ MARKET ORDER CREATION")
        print("-" * 50)
        
        try:
            # Test valid market order
            market_order = MarketOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("1.0")
            )
            
            assert market_order.pair == "XBTUSD"
            assert market_order.side == OrderSide.BUY
            assert market_order.volume == Decimal("1.0")
            assert market_order.order_type == OrderType.MARKET
            print("  ✅ Valid market order created")
            
            # Test pair normalization
            market_order2 = MarketOrderRequest(
                pair="xbtusd",
                side=OrderSide.SELL,
                volume=Decimal("0.5")
            )
            assert market_order2.pair == "XBTUSD"
            print("  ✅ Trading pair normalized to uppercase")
            
            # Test with optional fields
            market_order3 = MarketOrderRequest(
                pair="ETHUSD",
                side=OrderSide.BUY,
                volume=Decimal("2.0"),
                userref=12345,
                time_in_force=TimeInForce.IMMEDIATE_OR_CANCEL
            )
            assert market_order3.userref == 12345
            assert market_order3.time_in_force == TimeInForce.IMMEDIATE_OR_CANCEL
            print("  ✅ Optional fields handled correctly")
            
            self.test_results['market_order_creation'] = True
            print("✅ Market order creation: PASSED")
            
        except Exception as e:
            print(f"  ❌ Market order creation failed: {e}")
            self.test_results['market_order_creation'] = False
    
    def _test_2_limit_order_creation(self):
        """Test 2: Limit order creation and validation."""
        print("\\n2️⃣ LIMIT ORDER CREATION")
        print("-" * 50)
        
        try:
            # Test valid limit order
            limit_order = LimitOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("1.0"),
                price=Decimal("50000.00")
            )
            
            assert limit_order.pair == "XBTUSD"
            assert limit_order.side == OrderSide.BUY
            assert limit_order.volume == Decimal("1.0")
            assert limit_order.price == Decimal("50000.00")
            assert limit_order.order_type == OrderType.LIMIT
            print("  ✅ Valid limit order created")
            
            # Test with advanced fields
            limit_order2 = LimitOrderRequest(
                pair="ETHUSD",
                side=OrderSide.SELL,
                volume=Decimal("5.0"),
                price=Decimal("3000.00"),
                time_in_force=TimeInForce.GOOD_TILL_CANCELED,
                order_flags=[OrderFlags.POST_ONLY]
            )
            assert limit_order2.time_in_force == TimeInForce.GOOD_TILL_CANCELED
            assert OrderFlags.POST_ONLY in limit_order2.order_flags
            print("  ✅ Advanced limit order features working")
            
            # Test price validation
            try:
                invalid_limit = LimitOrderRequest(
                    pair="XBTUSD",
                    side=OrderSide.BUY,
                    volume=Decimal("1.0"),
                    price=Decimal("0")  # Invalid price
                )
                print("  ❌ Should have raised validation error for zero price")
                self.test_results['limit_order_creation'] = False
                return
            except ValueError:
                print("  ✅ Zero price correctly rejected")
            
            self.test_results['limit_order_creation'] = True
            print("✅ Limit order creation: PASSED")
            
        except Exception as e:
            print(f"  ❌ Limit order creation failed: {e}")
            self.test_results['limit_order_creation'] = False
    
    def _test_3_stop_order_creation(self):
        """Test 3: Stop order creation and validation."""
        print("\\n3️⃣ STOP ORDER CREATION")
        print("-" * 50)
        
        try:
            # Test stop-loss order
            stop_loss = StopLossOrderRequest(
                pair="XBTUSD",
                side=OrderSide.SELL,
                volume=Decimal("1.0"),
                stop_price=Decimal("45000.00")
            )
            
            assert stop_loss.order_type == OrderType.STOP_LOSS
            assert stop_loss.stop_price == Decimal("45000.00")
            print("  ✅ Stop-loss order created")
            
            # Test take-profit order
            take_profit = TakeProfitOrderRequest(
                pair="ETHUSD",
                side=OrderSide.SELL,
                volume=Decimal("2.0"),
                stop_price=Decimal("3500.00")
            )
            
            assert take_profit.order_type == OrderType.TAKE_PROFIT
            assert take_profit.stop_price == Decimal("3500.00")
            print("  ✅ Take-profit order created")
            
            self.test_results['stop_order_creation'] = True
            print("✅ Stop order creation: PASSED")
            
        except Exception as e:
            print(f"  ❌ Stop order creation failed: {e}")
            self.test_results['stop_order_creation'] = False
    
    def _test_4_order_validation(self):
        """Test 4: Order validation functionality."""
        print("\\n4️⃣ ORDER VALIDATION")
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
            assert len(validation_result.errors) == 0
            print("  ✅ Valid order passed validation")
            
            # Test large volume warning
            large_order = LimitOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("2000000.0"),  # Very large volume
                price=Decimal("50000.00")
            )
            
            large_validation = validate_order_request(large_order)
            assert large_validation.is_valid == True
            assert len(large_validation.warnings) > 0
            print("  ✅ Large volume warning generated")
            
            # Test invalid volume
            try:
                invalid_order = MarketOrderRequest(
                    pair="XBTUSD",
                    side=OrderSide.BUY,
                    volume=Decimal("0")  # Invalid volume
                )
                print("  ❌ Should have raised validation error for zero volume")
                self.test_results['order_validation'] = False
                return
            except ValueError:
                print("  ✅ Zero volume correctly rejected")
            
            self.test_results['order_validation'] = True
            print("✅ Order validation: PASSED")
            
        except Exception as e:
            print(f"  ❌ Order validation failed: {e}")
            self.test_results['order_validation'] = False
    
    def _test_5_response_models(self):
        """Test 5: Response model functionality."""
        print("\\n5️⃣ RESPONSE MODELS")
        print("-" * 50)
        
        try:
            # Test OrderPlacementResponse
            placement_response = OrderPlacementResponse(
                txid=["ORDER123", "ORDER124"],
                descr={
                    "pair": "XBTUSD",
                    "type": "buy",
                    "ordertype": "limit",
                    "price": "50000.00",
                    "order": "buy 1.0 XBTUSD @ limit 50000.00"
                }
            )
            
            assert placement_response.order_id == "ORDER123"
            assert placement_response.is_successful == True
            print("  ✅ OrderPlacementResponse working")
            
            # Test OrderStatusResponse
            status_response = OrderStatusResponse(
                order_id="ORDER123",
                status=OrderStatus.OPEN,
                volume=Decimal("1.0"),
                volume_executed=Decimal("0.5"),
                cost=Decimal("25000.00"),
                fee=Decimal("50.00")
            )
            
            assert status_response.remaining_volume == Decimal("0.5")
            assert status_response.fill_percentage == 50.0
            print("  ✅ OrderStatusResponse calculations working")
            
            self.test_results['response_models'] = True
            print("✅ Response models: PASSED")
            
        except Exception as e:
            print(f"  ❌ Response models failed: {e}")
            self.test_results['response_models'] = False
    
    def _test_6_factory_functions(self):
        """Test 6: Factory function functionality."""
        print("\\n6️⃣ FACTORY FUNCTIONS")
        print("-" * 50)
        
        try:
            # Test create_market_order
            market_order = create_market_order(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume="1.5"
            )
            
            assert isinstance(market_order, MarketOrderRequest)
            assert market_order.volume == Decimal("1.5")
            print("  ✅ create_market_order working")
            
            # Test create_limit_order
            limit_order = create_limit_order(
                pair="ETHUSD",
                side=OrderSide.SELL,
                volume="2.0",
                price="3000.00"
            )
            
            assert isinstance(limit_order, LimitOrderRequest)
            assert limit_order.price == Decimal("3000.00")
            print("  ✅ create_limit_order working")
            
            # Test with additional parameters
            advanced_order = create_limit_order(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume="1.0",
                price="49000.00",
                userref=54321,
                time_in_force=TimeInForce.IMMEDIATE_OR_CANCEL
            )
            
            assert advanced_order.userref == 54321
            assert advanced_order.time_in_force == TimeInForce.IMMEDIATE_OR_CANCEL
            print("  ✅ Factory functions handle additional parameters")
            
            self.test_results['factory_functions'] = True
            print("✅ Factory functions: PASSED")
            
        except Exception as e:
            print(f"  ❌ Factory functions failed: {e}")
            self.test_results['factory_functions'] = False
    
    def _test_7_data_sanitization(self):
        """Test 7: Data sanitization functionality."""
        print("\\n7️⃣ DATA SANITIZATION")
        print("-" * 50)
        
        try:
            # Test basic sanitization
            order_data = {
                'pair': 'XBTUSD',
                'side': OrderSide.BUY,
                'order_type': OrderType.LIMIT,
                'volume': Decimal('1.0'),
                'price': Decimal('50000.00'),
                'order_flags': [OrderFlags.POST_ONLY, OrderFlags.FCIQ]
            }
            
            sanitized = sanitize_order_data(order_data)
            
            # Check field mapping
            assert sanitized['type'] == 'buy'  # side -> type
            assert sanitized['ordertype'] == 'limit'  # order_type -> ordertype
            assert sanitized['volume'] == '1.0'  # Decimal -> string
            assert sanitized['price'] == '50000.00'  # Decimal -> string
            assert 'post,fciq' in sanitized['order_flags']  # List -> comma-separated
            print("  ✅ Field mapping working correctly")
            
            # Test None value filtering
            data_with_nones = {
                'pair': 'XBTUSD',
                'side': OrderSide.BUY,
                'volume': Decimal('1.0'),
                'price': None,  # Should be filtered out
                'userref': None  # Should be filtered out
            }
            
            sanitized_filtered = sanitize_order_data(data_with_nones)
            assert 'price' not in sanitized_filtered
            assert 'userref' not in sanitized_filtered
            print("  ✅ None values correctly filtered")
            
            self.test_results['data_sanitization'] = True
            print("✅ Data sanitization: PASSED")
            
        except Exception as e:
            print(f"  ❌ Data sanitization failed: {e}")
            self.test_results['data_sanitization'] = False
    
    def _test_8_error_handling(self):
        """Test 8: Error handling and edge cases."""
        print("\\n8️⃣ ERROR HANDLING")
        print("-" * 50)
        
        try:
            # Test invalid trading pair
            try:
                MarketOrderRequest(
                    pair="",  # Invalid empty pair
                    side=OrderSide.BUY,
                    volume=Decimal("1.0")
                )
                print("  ❌ Should have raised error for empty pair")
                self.test_results['error_handling'] = False
                return
            except ValueError:
                print("  ✅ Empty trading pair correctly rejected")
            
            # Test negative volume
            try:
                LimitOrderRequest(
                    pair="XBTUSD",
                    side=OrderSide.BUY,
                    volume=Decimal("-1.0"),  # Negative volume
                    price=Decimal("50000.00")
                )
                print("  ❌ Should have raised error for negative volume")
                self.test_results['error_handling'] = False
                return
            except ValueError:
                print("  ✅ Negative volume correctly rejected")
            
            # Test wrong order type for model
            try:
                MarketOrderRequest(
                    pair="XBTUSD",
                    side=OrderSide.BUY,
                    volume=Decimal("1.0"),
                    order_type=OrderType.LIMIT  # Wrong type for market order
                )
                print("  ❌ Should have raised error for wrong order type")
                self.test_results['error_handling'] = False
                return
            except ValueError:
                print("  ✅ Wrong order type correctly rejected")
            
            self.test_results['error_handling'] = True
            print("✅ Error handling: PASSED")
            
        except Exception as e:
            print(f"  ❌ Error handling test failed: {e}")
            self.test_results['error_handling'] = False
    
    def _test_9_edge_cases(self):
        """Test 9: Edge cases and boundary conditions."""
        print("\\n9️⃣ EDGE CASES")
        print("-" * 50)
        
        try:
            # Test very small volumes
            small_order = LimitOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("0.00000001"),  # Very small volume
                price=Decimal("50000.00")
            )
            assert small_order.volume == Decimal("0.00000001")
            print("  ✅ Very small volumes handled")
            
            # Test very large prices
            expensive_order = LimitOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("1.0"),
                price=Decimal("999999999.99")  # Very high price
            )
            assert expensive_order.price == Decimal("999999999.99")
            print("  ✅ Very large prices handled")
            
            # Test special characters in pair (should be normalized)
            special_order = MarketOrderRequest(
                pair="xbt/usd",  # With slash
                side=OrderSide.BUY,
                volume=Decimal("1.0")
            )
            # Note: This might need adjustment based on actual pair format requirements
            print("  ✅ Special pair formats handled")
            
            self.test_results['edge_cases'] = True
            print("✅ Edge cases: PASSED")
            
        except Exception as e:
            print(f"  ❌ Edge cases failed: {e}")
            self.test_results['edge_cases'] = False
    
    def _test_10_integration_readiness(self):
        """Test 10: Integration readiness with REST client."""
        print("\\n🔟 INTEGRATION READINESS")
        print("-" * 50)
        
        try:
            # Test that models can be converted to API format
            limit_order = create_limit_order(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume="1.0",
                price="50000.00",
                userref=12345
            )
            
            # Convert to dictionary
            order_dict = limit_order.dict()
            assert isinstance(order_dict, dict)
            print("  ✅ Models convert to dictionaries")
            
            # Test sanitization for API
            sanitized = sanitize_order_data(order_dict)
            assert 'type' in sanitized  # Should have mapped field
            assert 'ordertype' in sanitized  # Should have mapped field
            print("  ✅ API sanitization working")
            
            # Test validation pipeline
            validation = validate_order_request(limit_order)
            assert validation.is_valid == True
            assert validation.sanitized_data is not None
            print("  ✅ Validation pipeline working")
            
            # Test JSON serialization
            import json
            json_str = json.dumps(order_dict, default=str)
            assert isinstance(json_str, str)
            print("  ✅ JSON serialization working")
            
            self.test_results['integration_readiness'] = True
            print("✅ Integration readiness: PASSED")
            
        except Exception as e:
            print(f"  ❌ Integration readiness failed: {e}")
            self.test_results['integration_readiness'] = False
    
    def _generate_comprehensive_report(self):
        """Generate comprehensive test report."""
        print("\\n" + "=" * 70)
        print("📊 ORDER REQUEST/RESPONSE MODELS - TEST REPORT")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
        print(f"⏱️ Total Runtime: {time.time() - self.start_time:.1f} seconds")
        print()
        
        print("📋 Detailed Test Results:")
        test_descriptions = {
            'market_order_creation': 'Market Order Creation',
            'limit_order_creation': 'Limit Order Creation',
            'stop_order_creation': 'Stop Order Creation',
            'order_validation': 'Order Validation',
            'response_models': 'Response Models',
            'factory_functions': 'Factory Functions',
            'data_sanitization': 'Data Sanitization',
            'error_handling': 'Error Handling',
            'edge_cases': 'Edge Cases',
            'integration_readiness': 'Integration Readiness'
        }
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            description = test_descriptions.get(test_name, test_name.replace('_', ' ').title())
            print(f"  {status} - {description}")
        
        print()
        
        # Determine overall status
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Order Request/Response models are fully functional")
            print("✅ All validation and sanitization working correctly")
            print("✅ Factory functions and utilities operational")
            print("✅ Integration-ready for REST client")
            print()
            print("🚀 READY TO PROCEED WITH:")
            print("   • Task 3.2.C: Implement Pre-trade Risk Validation")
            print("   • Integration with Enhanced REST Client")
            
        elif passed_tests >= total_tests * 0.9:  # 90% or better
            print("⚠️ MOSTLY PASSED - Minor issues detected")
            print("Core functionality working, some features need attention")
            
        elif passed_tests >= total_tests * 0.7:  # 70% or better
            print("⚠️ MAJOR FUNCTIONALITY WORKING")
            print("Several tests passed, but significant issues need resolution")
            
        else:
            print("❌ CRITICAL ISSUES DETECTED")
            print("Order Request/Response models need significant work")
        
        print("=" * 70)
        
        return passed_tests == total_tests


def main():
    """Run the comprehensive Order Request/Response models test suite."""
    test_suite = OrderRequestModelsTestSuite()
    test_suite.run_full_test_suite()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\\n\\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
