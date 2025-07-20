#!/usr/bin/env python3
"""
list_endpoints.py
Script to list all FastAPI endpoints from your application
"""

import sys
import json
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def list_endpoints_from_app():
    """Import the FastAPI app and list all endpoints"""
    try:
        from main import app
        
        print("🚀 FASTAPI ENDPOINTS")
        print("=" * 60)
        print()
        
        routes = []
        
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                methods = list(route.methods)
                if 'HEAD' in methods:
                    methods.remove('HEAD')
                if 'OPTIONS' in methods:
                    methods.remove('OPTIONS')
                
                for method in methods:
                    routes.append({
                        'method': method,
                        'path': route.path,
                        'name': getattr(route, 'name', 'unnamed'),
                        'tags': getattr(route, 'tags', [])
                    })
        
        # Sort by path
        routes.sort(key=lambda x: x['path'])
        
        # Group by tags/categories
        grouped = {}
        for route in routes:
            tags = route['tags'] or ['Untagged']
            for tag in tags:
                if tag not in grouped:
                    grouped[tag] = []
                grouped[tag].append(route)
        
        # Print grouped endpoints
        for tag, tag_routes in grouped.items():
            print(f"📂 {tag.upper()}")
            print("-" * 40)
            for route in tag_routes:
                print(f"  {route['method']:<8} {route['path']}")
                if route['name'] != 'unnamed':
                    print(f"          └─ {route['name']}")
            print()
        
        # Print summary
        total_endpoints = len(routes)
        print(f"📊 SUMMARY")
        print("-" * 40)
        print(f"Total endpoints: {total_endpoints}")
        
        # Count by method
        method_count = {}
        for route in routes:
            method = route['method']
            method_count[method] = method_count.get(method, 0) + 1
        
        for method, count in sorted(method_count.items()):
            print(f"{method}: {count}")
        
        return routes
        
    except Exception as e:
        print(f"❌ Failed to import FastAPI app: {e}")
        print("Make sure you're in the FastAPI project directory")
        return None

def export_endpoints_json():
    """Export endpoints to JSON file"""
    routes = list_endpoints_from_app()
    if routes:
        with open('endpoints.json', 'w') as f:
            json.dump(routes, f, indent=2)
        print(f"\n💾 Endpoints exported to: endpoints.json")

def export_endpoints_curl():
    """Export endpoints as curl commands"""
    try:
        from main import app
        
        routes = []
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                methods = list(route.methods)
                if 'HEAD' in methods:
                    methods.remove('HEAD')
                if 'OPTIONS' in methods:
                    methods.remove('OPTIONS')
                
                for method in methods:
                    routes.append({
                        'method': method,
                        'path': route.path
                    })
        
        print("\n🔧 CURL COMMANDS")
        print("=" * 60)
        
        base_url = "http://localhost:8000"
        
        for route in sorted(routes, key=lambda x: x['path']):
            method = route['method']
            path = route['path']
            
            if method == 'GET':
                print(f"curl -X GET \"{base_url}{path}\"")
            elif method == 'POST':
                print(f"curl -X POST \"{base_url}{path}\" -H \"Content-Type: application/json\" -d '{{}}'")
            elif method == 'PUT':
                print(f"curl -X PUT \"{base_url}{path}\" -H \"Content-Type: application/json\" -d '{{}}'")
            elif method == 'DELETE':
                print(f"curl -X DELETE \"{base_url}{path}\"")
        
    except Exception as e:
        print(f"❌ Failed to generate curl commands: {e}")

def main():
    print("📋 FASTAPI ENDPOINT DISCOVERY")
    print("=" * 80)
    print()
    
    choice = input("Choose output format:\n1) Detailed list\n2) JSON export\n3) Curl commands\n4) All\nChoice (1-4): ")
    
    if choice == '1':
        list_endpoints_from_app()
    elif choice == '2':
        export_endpoints_json()
    elif choice == '3':
        export_endpoints_curl()
    elif choice == '4':
        list_endpoints_from_app()
        export_endpoints_json() 
        export_endpoints_curl()
    else:
        list_endpoints_from_app()

if __name__ == "__main__":
    main()
