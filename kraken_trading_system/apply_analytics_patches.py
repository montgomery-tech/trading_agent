#!/usr/bin/env python3
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
