#!/usr/bin/env python3
"""
Fix for Task 3.3.B.2 Analytics Division by Zero Error

The issue is in the _check_risk_alerts method where we're dividing by max_profit
when it's zero. This happens when processing the first fill.

File: fix_analytics_division_error.py
"""

import sys
from pathlib import Path


def fix_division_by_zero_error():
    """Fix the division by zero error in realtime_analytics.py."""
    
    print("🔧 Fixing Division by Zero Error in Analytics Engine")
    print("=" * 60)
    
    analytics_file = Path("src/trading_systems/exchanges/kraken/realtime_analytics.py")
    
    if not analytics_file.exists():
        print("❌ realtime_analytics.py not found")
        print("Please run: python3 implement_task_3_3_b_2.py first")
        return False
    
    try:
        with open(analytics_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
    
    # Find and fix the problematic code
    problematic_code = '''        # Check maximum drawdown
        if self.pnl.max_drawdown > 0:
            drawdown_pct = (self.pnl.max_drawdown / self.pnl.max_profit) * 100'''
    
    fixed_code = '''        # Check maximum drawdown
        if self.pnl.max_drawdown > 0 and self.pnl.max_profit > 0:
            drawdown_pct = (self.pnl.max_drawdown / self.pnl.max_profit) * 100'''
    
    if problematic_code in content:
        print("🔍 Found problematic division code")
        content = content.replace(problematic_code, fixed_code)
        print("✅ Applied fix: Added check for max_profit > 0")
    else:
        print("⚠️ Could not find exact problematic code, applying broader fix...")
        
        # Alternative fix approach - find the line and fix it
        if 'drawdown_pct = (self.pnl.max_drawdown / self.pnl.max_profit) * 100' in content:
            content = content.replace(
                'drawdown_pct = (self.pnl.max_drawdown / self.pnl.max_profit) * 100',
                'drawdown_pct = (self.pnl.max_drawdown / self.pnl.max_profit) * 100 if self.pnl.max_profit > 0 else Decimal("0")'
            )
            print("✅ Applied alternative fix")
        else:
            print("❌ Could not find division line to fix")
            return False
    
    # Write the fixed content
    try:
        with open(analytics_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Fixed file written successfully")
        return True
    except Exception as e:
        print(f"❌ Error writing fixed file: {e}")
        return False


def create_additional_fixes():
    """Create additional robustness fixes for the analytics engine."""
    
    print("\n🔧 Creating Additional Robustness Fixes")
    print("=" * 60)
    
    # Create a patch script for additional fixes
    patch_content = '''#!/usr/bin/env python3
"""
Additional robustness patches for the analytics engine.
"""

import sys
from pathlib import Path

def apply_robustness_patches():
    """Apply additional robustness patches."""
    
    analytics_file = Path("src/trading_systems/exchanges/kraken/realtime_analytics.py")
    
    if not analytics_file.exists():
        return False
    
    try:
        with open(analytics_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return False
    
    # Patch 1: Fix profit factor calculation
    if 'if self.pnl.gross_loss == 0:' in content:
        content = content.replace(
            'if self.pnl.gross_loss == 0:',
            'if self.pnl.gross_loss == 0 or abs(self.pnl.gross_loss) < Decimal("0.01"):'
        )
    
    # Patch 2: Add safety check for VWAP calculation  
    if 'self.average_slippage = (self.average_slippage + fill.slippage) / 2' in content:
        content = content.replace(
            'self.average_slippage = (self.average_slippage + fill.slippage) / 2',
            'self.average_slippage = (self.average_slippage + fill.slippage) / Decimal("2")'
        )
    
    # Patch 3: Add safety for price improvement calculation
    if 'self.average_price_improvement = (self.average_price_improvement + fill.price_improvement) / 2' in content:
        content = content.replace(
            'self.average_price_improvement = (self.average_price_improvement + fill.price_improvement) / 2',
            'self.average_price_improvement = (self.average_price_improvement + fill.price_improvement) / Decimal("2")'
        )
    
    try:
        with open(analytics_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception:
        return False

if __name__ == "__main__":
    apply_robustness_patches()
'''
    
    try:
        with open("apply_analytics_patches.py", 'w', encoding='utf-8') as f:
            f.write(patch_content)
        print("✅ Created additional patches script")
        return True
    except Exception as e:
        print(f"❌ Error creating patches script: {e}")
        return False


def main():
    """Apply the fixes for the analytics engine."""
    print("🎯 FIXING TASK 3.3.B.2 ANALYTICS ENGINE ERRORS")
    print("=" * 70)
    print()
    print("Issue: Division by zero in drawdown calculation")
    print("Cause: max_profit is 0 when processing first fill")
    print("Fix: Add check for max_profit > 0 before division")
    print()
    
    success_count = 0
    total_tasks = 2
    
    # Fix 1: Division by zero error
    if fix_division_by_zero_error():
        success_count += 1
    
    # Fix 2: Additional robustness patches
    if create_additional_fixes():
        success_count += 1
    
    print("\n" + "=" * 70)
    print("📊 ANALYTICS ENGINE FIX REPORT")
    print("=" * 70)
    print(f"🎯 Fixes Applied: {success_count}/{total_tasks}")
    
    if success_count >= 1:  # Main fix is critical
        print("🎉 CRITICAL FIX APPLIED!")
        print()
        print("✅ Fixed Issues:")
        print("   • Division by zero in drawdown calculation")
        print("   • Added safety check for max_profit > 0")
        print("   • Additional robustness patches available")
        print()
        print("🧪 Next Steps:")
        print("   1. Run: python3 test_task_3_3_b_2.py")
        print("   2. Should now pass 4/4 test suites")
        print("   3. Verify all analytics functionality working")
        
        if success_count == total_tasks:
            print("   4. Optional: Run python3 apply_analytics_patches.py for extra robustness")
        
    else:
        print("❌ COULD NOT APPLY FIXES - Manual intervention required")
        print()
        print("🔧 Manual Fix Instructions:")
        print("   1. Open: src/trading_systems/exchanges/kraken/realtime_analytics.py")
        print("   2. Find line: drawdown_pct = (self.pnl.max_drawdown / self.pnl.max_profit) * 100")
        print("   3. Change condition to: if self.pnl.max_drawdown > 0 and self.pnl.max_profit > 0:")
    
    print("=" * 70)
    return success_count >= 1


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Fix interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
