#!/usr/bin/env python3
"""
toggle_live_trading.py
Safely toggle live trading on/off
"""

import os

def toggle_live_trading():
    """Toggle live trading setting"""
    
    env_file = ".env"
    
    if not os.path.exists(env_file):
        print("❌ .env file not found")
        return
    
    with open(env_file, "r") as f:
        lines = f.readlines()
    
    found = False
    for i, line in enumerate(lines):
        if line.startswith("ENABLE_LIVE_TRADING="):
            current_value = line.strip().split("=")[1].lower()
            
            if current_value == "true":
                lines[i] = "ENABLE_LIVE_TRADING=false\n"
                print("🔴 Live trading DISABLED")
                print("   System is now in sandbox mode")
            else:
                print("⚠️  ENABLING LIVE TRADING!")
                confirm = input("Are you sure? This will execute REAL trades! (yes/no): ")
                if confirm.lower() == "yes":
                    lines[i] = "ENABLE_LIVE_TRADING=true\n"
                    print("🟢 Live trading ENABLED")
                    print("   ⚠️  REAL trades will now be executed!")
                else:
                    print("❌ Live trading remains disabled")
                    return
            
            found = True
            break
    
    if not found:
        print("❌ ENABLE_LIVE_TRADING setting not found in .env")
        return
    
    with open(env_file, "w") as f:
        f.writelines(lines)
    
    print("\n📋 Remember to restart your FastAPI application:")
    print("   python3 main.py")

if __name__ == "__main__":
    toggle_live_trading()
