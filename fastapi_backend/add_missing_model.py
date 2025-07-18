#!/usr/bin/env python3
"""
Add the missing TradingPairSpreadUpdate model to spread_management.py
"""

def add_model_to_spread_management():
    """Add the missing model definition"""
    
    spread_file = "api/routes/spread_management.py"
    
    print(f"🔧 Adding missing model to {spread_file}...")
    
    # Read the file
    with open(spread_file, "r") as f:
        lines = f.readlines()
    
    # Find where to insert the model (after imports, before router)
    insert_index = None
    for i, line in enumerate(lines):
        if "router = APIRouter()" in line:
            insert_index = i
            break
    
    if insert_index is None:
        print("❌ Could not find router definition!")
        return False
    
    # Create the model definition
    model_definition = '''
# Models for spread management
from pydantic import BaseModel, Field

class TradingPairSpreadUpdate(BaseModel):
    """Model for updating trading pair spread"""
    spread_percentage: float = Field(..., ge=0, le=1, description="Spread percentage (0-1, e.g., 0.02 for 2%)")

'''
    
    # Check if model already exists
    content = ''.join(lines)
    if "class TradingPairSpreadUpdate" not in content:
        # Insert the model before the router
        lines.insert(insert_index, model_definition)
        print("✅ Added TradingPairSpreadUpdate model")
    else:
        print("⚠️  Model already exists")
    
    # Write back
    with open(spread_file, "w") as f:
        f.writelines(lines)
    
    return True

def verify_and_show():
    """Show the updated file structure"""
    
    spread_file = "api/routes/spread_management.py"
    
    print(f"\n📄 Updated {spread_file} (first 30 lines):")
    print("-" * 50)
    
    with open(spread_file, "r") as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines[:30]):
        if "TradingPairSpreadUpdate" in line:
            print(f">>> {i+1:3d}: {line.rstrip()}")
        else:
            print(f"    {i+1:3d}: {line.rstrip()}")

if __name__ == "__main__":
    print("🚀 Adding Missing Model")
    print("=" * 50)
    
    if add_model_to_spread_management():
        verify_and_show()
        
        print("\n✅ Model added successfully!")
        print("\n📋 Now you can start FastAPI:")
        print("   python3 main.py")
    else:
        print("\n❌ Failed to add model")
