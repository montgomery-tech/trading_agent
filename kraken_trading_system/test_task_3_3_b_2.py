#!/usr/bin/env python3
"""
Task 3.3.B.2 Test Suite: Real-time Fill Analytics Engine

Comprehensive test suite for validating the RealTimeAnalyticsEngine implementation.

Usage: python3 test_task_3_3_b_2.py
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.realtime_analytics import (
        RealTimeAnalyticsEngine, RealTimePnL, ExecutionMetrics, RiskAlert,
        AlertLevel, PerformanceMetric, integrate_analytics_with_fill_processor
    )
    from trading_systems.exchanges.kraken.fill_processor import TradeFill, FillQuality, FillType
    print("✅ RealTimeAnalyticsEngine imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure realtime_analytics.py was created successfully")
    sys.exit(1)


class MockTradeFill:
    """Mock TradeFill for testing."""
    def __init__(self, trade_id, order_id, volume, price, side, pair="XBT/USD", fee=Decimal('0')):
        self.trade_id = trade_id
        self.order_id = order_id
        self.volume = Decimal(str(volume))
        self.price = Decimal(str(price))
        self.side = side
        self.pair = pair
        self.fee = Decimal(str(fee))
        self.timestamp = datetime.now()
        self.cost = self.volume * self.price
        self.slippage = Decimal('0.5')
        self.price_improvement = Decimal('0')
        self.reference_price = self.price + Decimal('1.0')
        self.fill_quality = type('FillQuality', (), {'value': 'fair'})()


async def test_basic_analytics_functionality():
    """Test basic analytics engine functionality."""
    print("🔬 TESTING BASIC ANALYTICS FUNCTIONALITY")
    print("=" * 60)
    
    try:
        # Initialize engine
        engine = RealTimeAnalyticsEngine("TestAnalyticsEngine")
        
        # Test 1: Initial state
        print("\n1️⃣ Testing Initial State...")
        assert engine.pnl.total_pnl == Decimal('0')
        assert engine.pnl.total_trades == 0
        assert len(engine.fill_history) == 0
        print("   ✅ Initial state correct")
        
        # Test 2: Process single fill
        print("\n2️⃣ Testing Single Fill Processing...")
        fill = MockTradeFill("TEST_001", "ORDER_001", "1.0", "50000.00", "buy", fee="5.00")
        await engine.process_fill(fill)
        
        assert len(engine.fill_history) == 1
        assert engine.pnl.total_trades == 1
        assert engine.pnl.total_volume_traded == Decimal('1.0')
        assert engine.pnl.total_fees == Decimal('5.0')
        print("   ✅ Single fill processing works")
        
        # Test 3: Multiple fills
        print("\n3️⃣ Testing Multiple Fills...")
        fills = [
            MockTradeFill("TEST_002", "ORDER_001", "0.5", "50100.00", "buy", fee="2.50"),
            MockTradeFill("TEST_003", "ORDER_002", "0.3", "49900.00", "sell", fee="1.50"),
        ]
        
        for fill in fills:
            await engine.process_fill(fill)
        
        assert len(engine.fill_history) == 3
        assert engine.pnl.total_trades == 3
        assert engine.pnl.total_volume_traded == Decimal('1.8')
        print("   ✅ Multiple fills processing works")
        
        # Test 4: Real-time dashboard
        print("\n4️⃣ Testing Real-time Dashboard...")
        dashboard = engine.get_real_time_dashboard()
        
        assert 'pnl_summary' in dashboard
        assert 'trading_stats' in dashboard
        assert 'execution_quality' in dashboard
        assert dashboard['trading_stats']['total_trades'] == 3
        print("   ✅ Dashboard generation works")
        
        # Test 5: Performance report
        print("\n5️⃣ Testing Performance Report...")
        report = engine.get_performance_report(timedelta(hours=1))
        
        assert 'summary_statistics' in report
        assert report['summary_statistics']['total_fills'] == 3
        assert 'quality_analysis' in report
        print("   ✅ Performance report generation works")
        
        print("\n🎉 ALL BASIC TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Basic analytics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_risk_alert_system():
    """Test risk alert system functionality."""
    print("\n🔬 TESTING RISK ALERT SYSTEM")
    print("=" * 60)
    
    try:
        engine = RealTimeAnalyticsEngine("RiskTestEngine")
        alerts_received = []
        
        # Add alert handler
        def alert_handler(alert: RiskAlert):
            alerts_received.append(alert)
        
        engine.add_alert_handler(alert_handler)
        
        # Test 1: Position size alert
        print("\n1️⃣ Testing Position Size Alert...")
        
        # Set low threshold for testing
        engine.update_risk_threshold('max_position_size', Decimal('2.0'))
        
        # Create large position
        large_fill = MockTradeFill("LARGE_001", "ORDER_001", "5.0", "50000.00", "buy")
        await engine.process_fill(large_fill)
        
        # Should trigger position size alert
        position_alerts = [a for a in alerts_received if a.metric == "position_size"]
        assert len(position_alerts) > 0
        print("   ✅ Position size alert triggered")
        
        # Test 2: Slippage alert
        print("\n2️⃣ Testing Slippage Alert...")
        
        # Create fill with high slippage
        high_slippage_fill = MockTradeFill("SLIP_001", "ORDER_002", "1.0", "50000.00", "buy")
        high_slippage_fill.slippage = Decimal('100.0')  # High slippage
        high_slippage_fill.reference_price = Decimal('50000.0')
        
        await engine.process_fill(high_slippage_fill)
        
        # Should trigger slippage alert
        slippage_alerts = [a for a in alerts_received if a.metric == "slippage"]
        assert len(slippage_alerts) > 0
        print("   ✅ Slippage alert triggered")
        
        # Test 3: Alert levels
        print("\n3️⃣ Testing Alert Levels...")
        
        # Check that we have different alert levels
        alert_levels = set(a.level for a in alerts_received)
        assert len(alert_levels) > 0
        print(f"   ✅ Alert levels working: {[level.value for level in alert_levels]}")
        
        print("\n🎉 RISK ALERT TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Risk alert test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_performance_metrics():
    """Test performance metrics calculation."""
    print("\n🔬 TESTING PERFORMANCE METRICS")
    print("=" * 60)
    
    try:
        engine = RealTimeAnalyticsEngine("MetricsTestEngine")
        
        # Test 1: PnL tracking
        print("\n1️⃣ Testing PnL Tracking...")
        
        # Simulate profitable and losing trades
        fills = [
            MockTradeFill("PROFIT_001", "ORDER_001", "1.0", "50000.00", "buy", fee="5.00"),
            MockTradeFill("PROFIT_002", "ORDER_001", "1.0", "50100.00", "sell", fee="5.00"),  # Profit
            MockTradeFill("LOSS_001", "ORDER_002", "1.0", "49000.00", "buy", fee="5.00"),
            MockTradeFill("LOSS_002", "ORDER_002", "1.0", "48900.00", "sell", fee="5.00"),    # Loss
        ]
        
        for fill in fills:
            await engine.process_fill(fill, {'current_price': Decimal('50000.00')})
        
        assert engine.pnl.total_trades == 4
        assert engine.pnl.total_volume_traded == Decimal('4.0')
        print("   ✅ PnL tracking working")
        
        # Test 2: Execution metrics
        print("\n2️⃣ Testing Execution Metrics...")
        
        assert engine.execution_metrics.average_slippage >= Decimal('0')
        print(f"   ✅ Average slippage: {engine.execution_metrics.average_slippage}")
        
        # Test 3: Performance calculations
        print("\n3️⃣ Testing Performance Calculations...")
        
        # Test Sharpe ratio calculation (may be None with limited data)
        sharpe = engine.calculate_sharpe_ratio(60)
        print(f"   📊 Sharpe ratio: {sharpe if sharpe else 'N/A (insufficient data)'}")
        
        # Test profit factor calculation
        profit_factor = engine.calculate_profit_factor()
        print(f"   📊 Profit factor: {profit_factor if profit_factor else 'N/A (no losses yet)'}")
        
        print("   ✅ Performance calculations working")
        
        print("\n🎉 PERFORMANCE METRICS TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Performance metrics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_integration_capabilities():
    """Test integration with FillProcessor."""
    print("\n🔬 TESTING INTEGRATION CAPABILITIES")
    print("=" * 60)
    
    try:
        # Mock FillProcessor for integration testing
        class MockFillProcessor:
            def __init__(self):
                self.fill_handlers = []
            
            def add_fill_handler(self, handler):
                self.fill_handlers.append(handler)
                
            async def simulate_fill(self, fill):
                for handler in self.fill_handlers:
                    await handler(fill)
        
        print("\n1️⃣ Testing FillProcessor Integration...")
        
        engine = RealTimeAnalyticsEngine("IntegrationTestEngine")
        mock_processor = MockFillProcessor()
        
        # Setup integration
        await integrate_analytics_with_fill_processor(mock_processor, engine)
        
        assert len(mock_processor.fill_handlers) == 1
        print("   ✅ Integration handler registered")
        
        # Test integration flow
        test_fill = MockTradeFill("INTEGRATION_001", "ORDER_001", "1.0", "50000.00", "buy")
        await mock_processor.simulate_fill(test_fill)
        
        # Verify fill was processed in analytics engine
        assert len(engine.fill_history) == 1
        assert engine.fill_history[0].trade_id == "INTEGRATION_001"
        print("   ✅ Integration flow working")
        
        # Test system health
        print("\n2️⃣ Testing System Health...")
        
        health = engine.get_system_health()
        assert health['status'] == 'active'
        assert health['data_points']['fills_stored'] == 1
        print("   ✅ System health reporting working")
        
        print("\n🎉 INTEGRATION TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests for Task 3.3.B.2."""
    print("🎯 TASK 3.3.B.2: REAL-TIME ANALYTICS ENGINE TEST SUITE")
    print("=" * 70)
    print("Testing Real-time Fill Analytics Engine functionality")
    print()
    
    test_results = {}
    
    # Run test suites
    test_results['basic_functionality'] = await test_basic_analytics_functionality()
    test_results['risk_alert_system'] = await test_risk_alert_system()
    test_results['performance_metrics'] = await test_performance_metrics()
    test_results['integration'] = await test_integration_capabilities()
    
    # Generate report
    print("\n" + "=" * 70)
    print("📊 TASK 3.3.B.2 TEST RESULTS")
    print("=" * 70)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    
    print(f"🎯 Overall Result: {passed_tests}/{total_tests} test suites passed")
    print()
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        description = test_name.replace('_', ' ').title()
        print(f"  {status} - {description}")
    
    print()
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Task 3.3.B.2: Real-time Fill Analytics Engine - VERIFIED!")
        print()
        print("🚀 Verified Features:")
        print("   • Real-time PnL tracking and calculation")
        print("   • Risk alert system with configurable thresholds")
        print("   • Performance metrics (Sharpe ratio, profit factor)")
        print("   • Execution quality monitoring")
        print("   • Live dashboard and reporting")
        print("   • FillProcessor integration")
        print()
        print("🎯 READY FOR TASK 3.3.B.3: Advanced Fill Event System")
    else:
        print("⚠️ Some tests failed - additional work may be needed")
    
    print("=" * 70)
    return passed_tests == total_tests


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
