#!/usr/bin/env python3
"""
Updated Test Script for Order Request/Response Models - Pydantic V2 Compatible

This updated test script fixes compatibility issues and tests the corrected models.

Save as: test_order_models_fixed.py
Run with: python3 test_order_models_fixed.py
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
    print("1. Apply the fixes to order_requests.py first")
    print("2. Ensure all required files exist in the correct directory structure")
    print("3. Check that account_models.py exists and contains OrderSide, OrderType, OrderStatus")
    sys.exit(1)


class FixedOrderModelsTestSuite:
    """Updated test suite for Order Request/Response models."""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()
        
    def run_full_test_suite(self):
        """Run the complete test suite with fixes applied."""
        print("🧪 ORDER REQUEST/RESPONSE MODELS - FIXED TEST SUITE")
        print("=" * 70)
        print("Testing all fixed Order Request/Response model functionality")
        print("=" * 70)
        
        try:
            # Test Categories
            self._test_1_market_order_creation()
            self._test_2_limit_order_creation()
            self._test_3_stop_order_creation_fixed()
            self._test_4_order_validation()
            self._test_5_response_models()
            self._test_6_factory_functions()
            self._test_7_data_sanitization_fixed()
            self._test_8_error_handling()
            self._test_9_pydantic_v2_compatibility()
            self._test_10_integration_readiness_fixed()
            
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self._generate_comprehensive_report()
    
    def _test_1_market_order_creation(self):
        """Test 1: Market order creation (unchanged)."""
        print("\\n1️⃣ MARKET ORDER CREATION")
        print("-" * 50)
        
        try:
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
            
            self.test_results['market_order_creation'] = True
            print("✅ Market order creation: PASSED")
            
        except Exception as e:
            print(f"  ❌ Market order creation failed: {e}")
            self.test_results['market_order_creation'] = False
    
    def _test_2_limit_order_creation(self):
        """Test 2: Limit order creation (unchanged)."""
        print("\\n2️⃣ LIMIT ORDER CREATION")
        print("-" * 50)
        
        try:
            limit_order = LimitOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("1.0"),
                price=Decimal("50000.00")
            )
            
            assert limit_order.pair == "XBTUSD"
            assert limit_order.price == Decimal("50000.00")
            print("  ✅ Valid limit order created")
            
            self.test_results['limit_order_creation'] = True
            print("✅ Limit order creation: PASSED")
            
        except Exception as e:
            print(f"  ❌ Limit order creation failed: {e}")
            self.test_results['limit_order_creation'] = False
    
    def _test_3_stop_order_creation_fixed(self):
        """Test 3: Stop order creation (FIXED)."""
        print("\\n3️⃣ STOP ORDER CREATION (FIXED)")
        print("-" * 50)
        
        try:
            # Test stop-loss order with corrected field name
            stop_loss = StopLossOrderRequest(
                pair="XBTUSD",
                side=OrderSide.SELL,
                volume=Decimal("1.0"),
                price=Decimal("45000.00")  # Changed from stop_price to price
            )
            
            assert stop_loss.order_type == OrderType.STOP_LOSS
            assert stop_loss.price == Decimal("45000.00")
            print("  ✅ Stop-loss order created with correct field mapping")
            
            # Test take-profit order
            take_profit = TakeProfitOrderRequest(
                pair="ETHUSD",
                side=OrderSide.SELL,
                volume=Decimal("2.0"),
                price=Decimal("3500.00")  # Changed from stop_price to price
            )
            
            assert take_profit.order_type == OrderType.TAKE_PROFIT
            assert take_profit.price == Decimal("3500.00")
            print("  ✅ Take-profit order created with correct field mapping")
            
            self.test_results['stop_order_creation_fixed'] = True
            print("✅ Stop order creation (FIXED): PASSED")
            
        except Exception as e:
            print(f"  ❌ Stop order creation failed: {e}")
            self.test_results['stop_order_creation_fixed'] = False
    
    def _test_4_order_validation(self):
        """Test 4: Order validation (unchanged)."""
        print("\\n4️⃣ ORDER VALIDATION")
        print("-" * 50)
        
        try:
            valid_order = LimitOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("1.0"),
                price=Decimal("50000.00")
            )
            
            validation_result = validate_order_request(valid_order)
            assert validation_result.is_valid == True
            print("  ✅ Valid order passed validation")
            
            self.test_results['order_validation'] = True
            print("✅ Order validation: PASSED")
            
        except Exception as e:
            print(f"  ❌ Order validation failed: {e}")
            self.test_results['order_validation'] = False
    
    def _test_5_response_models(self):
        """Test 5: Response models (unchanged)."""
        print("\\n5️⃣ RESPONSE MODELS")
        print("-" * 50)
        
        try:
            placement_response = OrderPlacementResponse(
                txid=["ORDER123"],
                descr={
                    "pair": "XBTUSD",
                    "type": "buy",
                    "ordertype": "limit",
                    "price": "50000.00",
                    "order": "buy 1.0 XBTUSD @ limit 50000.00"
                }
            )
            
            assert placement_response.is_successful == True
            print("  ✅ OrderPlacementResponse working")
            
            self.test_results['response_models'] = True
            print("✅ Response models: PASSED")
            
        except Exception as e:
            print(f"  ❌ Response models failed: {e}")
            self.test_results['response_models'] = False
    
    def _test_6_factory_functions(self):
        """Test 6: Factory functions (unchanged)."""
        print("\\n6️⃣ FACTORY FUNCTIONS")
        print("-" * 50)
        
        try:
            market_order = create_market_order(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume="1.5"
            )
            
            assert isinstance(market_order, MarketOrderRequest)
            print("  ✅ create_market_order working")
            
            limit_order = create_limit_order(
                pair="ETHUSD",
                side=OrderSide.SELL,
                volume="2.0",
                price="3000.00"
            )
            
            assert isinstance(limit_order, LimitOrderRequest)
            print("  ✅ create_limit_order working")
            
            self.test_results['factory_functions'] = True
            print("✅ Factory functions: PASSED")
            
        except Exception as e:
            print(f"  ❌ Factory functions failed: {e}")
            self.test_results['factory_functions'] = False
    
    def _test_7_data_sanitization_fixed(self):
        """Test 7: Data sanitization (FIXED)."""
        print("\\n7️⃣ DATA SANITIZATION (FIXED)")
        print("-" * 50)
        
        try:
            # Test improved sanitization
            order_data = {
                'pair': 'XBTUSD',
                'side': OrderSide.BUY,
                'order_type': OrderType.LIMIT,
                'volume': Decimal('1.0'),
                'price': Decimal('50000.00'),
                'order_flags': [OrderFlags.POST_ONLY]
            }
            
            sanitized = sanitize_order_data(order_data)
            
            # Check field mapping
            assert sanitized['type'] == 'buy'  # side -> type
            assert sanitized['ordertype'] == 'limit'  # order_type -> ordertype
            assert sanitized['volume'] == '1.0'  # Decimal -> string
            assert sanitized['price'] == '50000.00'  # Decimal -> string
            assert 'post' in sanitized['order_flags']  # Enum list -> string
            print("  ✅ Enhanced field mapping working correctly")
            
            # Test empty list handling
            data_with_empty_list = {
                'pair': 'XBTUSD',
                'side': OrderSide.BUY,
                'volume': Decimal('1.0'),
                'order_flags': []  # Empty list
            }
            
            sanitized_empty = sanitize_order_data(data_with_empty_list)
            assert 'order_flags' not in sanitized_empty  # Empty list should be excluded
            print("  ✅ Empty lists correctly handled")
            
            self.test_results['data_sanitization_fixed'] = True
            print("✅ Data sanitization (FIXED): PASSED")
            
        except Exception as e:
            print(f"  ❌ Data sanitization failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['data_sanitization_fixed'] = False
    
    def _test_8_error_handling(self):
        """Test 8: Error handling (unchanged)."""
        print("\\n8️⃣ ERROR HANDLING")
        print("-" * 50)
        
        try:
            # Test invalid trading pair
            try:
                MarketOrderRequest(
                    pair="",
                    side=OrderSide.BUY,
                    volume=Decimal("1.0")
                )
                print("  ❌ Should have raised error for empty pair")
                self.test_results['error_handling'] = False
                return
            except ValueError:
                print("  ✅ Empty trading pair correctly rejected")
            
            self.test_results['error_handling'] = True
            print("✅ Error handling: PASSED")
            
        except Exception as e:
            print(f"  ❌ Error handling test failed: {e}")
            self.test_results['error_handling'] = False
    
    def _test_9_pydantic_v2_compatibility(self):
        """Test 9: Pydantic V2 compatibility (NEW)."""
        print("\\n9️⃣ PYDANTIC V2 COMPATIBILITY")
        print("-" * 50)
        
        try:
            # Test model_dump instead of dict
            limit_order = LimitOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("1.0"),
                price=Decimal("50000.00")
            )
            
            # Use model_dump (Pydantic V2)
            order_dict = limit_order.model_dump()
            assert isinstance(order_dict, dict)
            assert 'pair' in order_dict
            print("  ✅ model_dump() working correctly")
            
            # Test model_dump with exclude
            order_dict_minimal = limit_order.model_dump(exclude={'userref', 'validate_only'})
            assert 'userref' not in order_dict_minimal
            print("  ✅ model_dump() with exclude working")
            
            # Test alias handling
            order_dict_alias = limit_order.model_dump(by_alias=True)
            assert isinstance(order_dict_alias, dict)
            print("  ✅ model_dump() with alias support working")
            
            self.test_results['pydantic_v2_compatibility'] = True
            print("✅ Pydantic V2 compatibility: PASSED")
            
        except Exception as e:
            print(f"  ❌ Pydantic V2 compatibility failed: {e}")
            self.test_results['pydantic_v2_compatibility'] = False
    
    def _test_10_integration_readiness_fixed(self):
        """Test 10: Integration readiness (FIXED)."""
        print("\\n🔟 INTEGRATION READINESS (FIXED)")
        print("-" * 50)
        
        try:
            limit_order = create_limit_order(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume="1.0",
                price="50000.00"
            )
            
            # Use model_dump instead of deprecated dict()
            order_dict = limit_order.model_dump()
            assert isinstance(order_dict, dict)
            print("  ✅ Models convert to dictionaries (Pydantic V2)")
            
            # Test sanitization
            sanitized = sanitize_order_data(order_dict)
            assert 'type' in sanitized
            assert 'ordertype' in sanitized
            print("  ✅ API sanitization working")
            
            # Test validation pipeline
            validation = validate_order_request(limit_order)
            assert validation.is_valid == True
            print("  ✅ Validation pipeline working")
            
            self.test_results['integration_readiness_fixed'] = True
            print("✅ Integration readiness (FIXED): PASSED")
            
        except Exception as e:
            print(f"  ❌ Integration readiness failed: {e}")
            self.test_results['integration_readiness_fixed'] = False
    
    def _generate_comprehensive_report(self):
        """Generate comprehensive test report."""
        print("\\n" + "=" * 70)
        print("📊 ORDER REQUEST/RESPONSE MODELS - FIXED TEST REPORT")
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
            'stop_order_creation_fixed': 'Stop Order Creation (FIXED)',
            'order_validation': 'Order Validation',
            'response_models': 'Response Models',
            'factory_functions': 'Factory Functions',
            'data_sanitization_fixed': 'Data Sanitization (FIXED)',
            'error_handling': 'Error Handling',
            'pydantic_v2_compatibility': 'Pydantic V2 Compatibility (NEW)',
            'integration_readiness_fixed': 'Integration Readiness (FIXED)'
        }
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            description = test_descriptions.get(test_name, test_name.replace('_', ' ').title())
            print(f"  {status} - {description}")
        
        print()
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Order Request/Response models fully functional and fixed")
            print("✅ Pydantic V2 compatibility achieved")
            print("✅ Stop order field mapping corrected")
            print("✅ Data sanitization enhanced")
            print("✅ Ready for integration with Enhanced REST Client")
            print()
            print("🚀 READY TO PROCEED WITH:")
            print("   • Task 3.2.C: Implement Pre-trade Risk Validation")
            print("   • Integration testing with real API")
            
        elif passed_tests >= total_tests * 0.9:
            print("⚠️ MOSTLY PASSED - Minor issues remain")
            
        else:
            print("❌ SIGNIFICANT ISSUES - More fixes needed")
        
        print("=" * 70)
        
        return passed_tests == total_tests


def main():
    """Run the fixed Order Request/Response models test suite."""
    test_suite = FixedOrderModelsTestSuite()
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
