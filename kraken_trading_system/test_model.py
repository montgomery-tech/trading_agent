#!/usr/bin/env python3
"""
Simple test to check imports and run basic order model validation.
This bypasses pytest configuration issues.
"""

import sys
import os
from pathlib import Path

# Add various possible paths to sys.path
project_root = Path(__file__).parent.parent.parent if 'tests' in str(Path(__file__)) else Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

print(f"🔍 Testing imports from: {project_root}")
print(f"Python path includes: {[str(p) for p in [project_root / 'src', project_root]]}")

# Try different import combinations
import_attempts = [
    # src/trading_systems structure
    ("trading_systems.exchanges.kraken.account_models", "OrderSide, OrderType, OrderStatus"),
    ("trading_systems.exchanges.kraken.order_models", "OrderState, OrderEvent"),

    # src/trading_system structure
    ("trading_system.exchanges.kraken.account_models", "OrderSide, OrderType, OrderStatus"),
    ("trading_system.exchanges.kraken.order_models", "OrderState, OrderEvent"),

    # Direct structure (no src)
    ("exchanges.kraken.account_models", "OrderSide, OrderType, OrderStatus"),
    ("exchanges.kraken.order_models", "OrderState, OrderEvent"),
]

successful_imports = {}

for module_path, items in import_attempts:
    try:
        module = __import__(module_path, fromlist=items.split(", "))
        successful_imports[module_path] = module
        print(f"✅ Successfully imported: {module_path}")

        # Try to access the items
        for item in items.split(", "):
            if hasattr(module, item):
                print(f"   ✅ Found: {item}")
            else:
                print(f"   ❌ Missing: {item}")

    except ImportError as e:
        print(f"❌ Failed to import {module_path}: {e}")

if successful_imports:
    print(f"\n🎉 SUCCESS! Found working imports:")
    for module_path in successful_imports:
        print(f"   from {module_path} import ...")

    # Now let's test the actual functionality
    print(f"\n🧪 TESTING ORDER MODEL FUNCTIONALITY")
    print("-" * 50)

    # Find the account models module
    account_module = None
    order_module = None

    for module_path, module in successful_imports.items():
        if 'account_models' in module_path:
            account_module = module
        elif 'order_models' in module_path:
            order_module = module

    if account_module:
        print("✅ Testing account models...")
        try:
            OrderSide = account_module.OrderSide
            OrderType = account_module.OrderType
            OrderStatus = account_module.OrderStatus
            print(f"   ✅ OrderSide values: {list(OrderSide)}")
            print(f"   ✅ OrderType values: {list(OrderType)}")
            print(f"   ✅ OrderStatus values: {list(OrderStatus)}")
        except Exception as e:
            print(f"   ❌ Error testing account models: {e}")

    if order_module:
        print("✅ Testing order models...")
        try:
            OrderState = order_module.OrderState
            OrderEvent = order_module.OrderEvent
            print(f"   ✅ OrderState values: {list(OrderState)}")
            print(f"   ✅ OrderEvent values: {list(OrderEvent)}")

            # Test state machine
            OrderStateMachine = order_module.OrderStateMachine
            valid = OrderStateMachine.is_valid_transition(OrderState.PENDING_NEW, OrderState.PENDING_SUBMIT)
            print(f"   ✅ State machine test: PENDING_NEW -> PENDING_SUBMIT = {valid}")

        except Exception as e:
            print(f"   ❌ Error testing order models: {e}")

    print(f"\n🎯 BASIC FUNCTIONALITY TEST COMPLETE")

else:
    print(f"\n❌ No successful imports found. The order_models.py file may not exist yet.")
    print(f"📁 Checking if files exist:")

    # Check common locations
    possible_files = [
        project_root / "src" / "trading_systems" / "exchanges" / "kraken" / "order_models.py",
        project_root / "src" / "trading_system" / "exchanges" / "kraken" / "order_models.py",
        project_root / "trading_systems" / "exchanges" / "kraken" / "order_models.py",
        project_root / "trading_system" / "exchanges" / "kraken" / "order_models.py",
    ]

    for file_path in possible_files:
        exists = file_path.exists()
        print(f"   {'✅' if exists else '❌'} {file_path}")

        if exists:
            print(f"      📊 Size: {file_path.stat().st_size} bytes")

    print(f"\n📝 NEXT STEPS:")
    print(f"   1. If order_models.py doesn't exist, we need to create it")
    print(f"   2. If it exists but imports fail, we need to fix the content")
    print(f"   3. Once imports work, we can run the full test suite")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 SIMPLE IMPORT AND FUNCTIONALITY TEST")
    print("=" * 60)
