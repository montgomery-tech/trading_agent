#!/usr/bin/env python3
"""
MCP Server Installation and Test Script

This script sets up the MCP server environment and provides testing utilities.

File Location: install_mcp_server.py (in project root)
"""

import subprocess
import sys
import os
from pathlib import Path
import asyncio


def install_mcp_dependencies():
    """Install MCP SDK and dependencies."""
    print("🔧 Installing MCP SDK dependencies...")
    
    try:
        # Install the MCP SDK with CLI tools
        subprocess.run([
            sys.executable, "-m", "pip", "install", "mcp[cli]"
        ], check=True)
        
        print("✅ MCP SDK installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install MCP SDK: {e}")
        return False


def update_project_dependencies():
    """Update project dependencies to include MCP."""
    print("📦 Updating project dependencies...")
    
    project_root = Path(__file__).parent
    
    try:
        # Install project in development mode with new dependencies
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-e", "."
        ], cwd=project_root, check=True)
        
        print("✅ Project dependencies updated")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to update dependencies: {e}")
        return False


def test_mcp_imports():
    """Test that MCP imports work correctly."""
    print("🧪 Testing MCP imports...")
    
    try:
        from mcp.server.fastmcp import FastMCP
        from mcp.types import TextContent
        print("✅ MCP SDK imports successful")
        return True
        
    except ImportError as e:
        print(f"❌ MCP import failed: {e}")
        return False


def test_trading_system_imports():
    """Test that trading system imports work."""
    print("🧪 Testing trading system imports...")
    
    project_root = Path(__file__).parent
    src_path = project_root / "src"
    
    # Add src to path temporarily
    sys.path.insert(0, str(src_path))
    
    try:
        from trading_systems.config.settings import settings
        from trading_systems.utils.logger import get_logger
        print("✅ Trading system imports successful")
        return True
        
    except ImportError as e:
        print(f"❌ Trading system import failed: {e}")
        print("💡 This is expected if trading system components aren't fully implemented yet")
        return False
    finally:
        sys.path.remove(str(src_path))


def create_mcp_server_files():
    """Create the MCP server directory structure if it doesn't exist."""
    print("📁 Creating MCP server directory structure...")
    
    project_root = Path(__file__).parent
    mcp_server_dir = project_root / "src" / "trading_systems" / "mcp_server"
    
    # Create directory
    mcp_server_dir.mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py if it doesn't exist
    init_file = mcp_server_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""MCP Server module."""\n')
    
    print(f"✅ MCP server directory created: {mcp_server_dir}")
    return True


async def test_mcp_server_basic():
    """Test basic MCP server functionality."""
    print("🚀 Testing basic MCP server...")
    
    project_root = Path(__file__).parent
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))
    
    try:
        # Import our MCP server components
        from trading_systems.mcp_server.config import MCPServerConfig
        from trading_systems.mcp_server.trading_adapter import TradingSystemAdapter
        
        # Test configuration
        config = MCPServerConfig()
        print(f"✅ MCP server config created: {config.server_name}")
        
        # Test adapter in demo mode
        adapter = TradingSystemAdapter(config)
        await adapter.initialize()
        
        status = adapter.get_status()
        print(f"✅ Trading adapter status: {status.connection_details}")
        
        await adapter.shutdown()
        print("✅ Basic MCP server test successful")
        return True
        
    except Exception as e:
        print(f"❌ MCP server test failed: {e}")
        return False
    finally:
        if str(src_path) in sys.path:
            sys.path.remove(str(src_path))


def test_mcp_inspector():
    """Test the MCP Inspector tool."""
    print("🔍 Testing MCP Inspector availability...")
    
    try:
        result = subprocess.run([
            "mcp", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ MCP CLI tools available")
            print("💡 You can test the server with: mcp dev src/trading_systems/mcp_server/main.py")
            return True
        else:
            print("❌ MCP CLI tools not available")
            return False
            
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"❌ MCP CLI test failed: {e}")
        return False


def main():
    """Main installation and test function."""
    print("🎯 KRAKEN TRADING SYSTEM - MCP SERVER SETUP")
    print("=" * 60)
    
    # Track success/failure of each step
    results = {}
    
    # Step 1: Install MCP dependencies
    results["dependencies"] = install_mcp_dependencies()
    
    # Step 2: Create directory structure
    results["directories"] = create_mcp_server_files()
    
    # Step 3: Update project dependencies
    results["project_deps"] = update_project_dependencies()
    
    # Step 4: Test MCP imports
    results["mcp_imports"] = test_mcp_imports()
    
    # Step 5: Test trading system imports
    results["trading_imports"] = test_trading_system_imports()
    
    # Step 6: Test MCP CLI tools
    results["mcp_cli"] = test_mcp_inspector()
    
    # Step 7: Test basic server functionality
    if all([results["dependencies"], results["mcp_imports"]]):
        try:
            results["server_test"] = asyncio.run(test_mcp_server_basic())
        except Exception as e:
            print(f"❌ Server test failed: {e}")
            results["server_test"] = False
    else:
        print("⏭️ Skipping server test due to dependency issues")
        results["server_test"] = False
    
    # Report results
    print("\n📊 INSTALLATION RESULTS")
    print("=" * 60)
    
    for step, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {step}")
    
    # Overall status
    if all(results.values()):
        print("\n🎉 MCP SERVER SETUP COMPLETE!")
        print("\n🚀 Next steps:")
        print("1. Run: mcp dev src/trading_systems/mcp_server/main.py")
        print("2. Test with MCP Inspector")
        print("3. Integrate with Claude Desktop")
        
    elif results["dependencies"] and results["mcp_imports"]:
        print("\n⚠️ PARTIAL SUCCESS - Basic MCP functionality available")
        print("💡 Some trading system components may need implementation")
        
    else:
        print("\n❌ SETUP FAILED - Please check error messages above")
        print("💡 Try running: pip install 'mcp[cli]'")


if __name__ == "__main__":
    main()
