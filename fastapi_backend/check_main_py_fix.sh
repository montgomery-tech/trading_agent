#!/bin/bash

echo "🔍 Checking main.py Fix Result"
echo "=============================="

echo "📋 Current admin router section in main.py:"
echo "-------------------------------------------"

# Show the admin router section
grep -n -A 5 -B 5 -i "admin" main.py

echo ""
echo "📋 All app.include_router calls:"
echo "--------------------------------"

# Show all router inclusions
grep -n -A 3 -B 1 "app.include_router" main.py

echo ""
echo "🔍 Looking for syntax issues around admin router..."

# Check for potential syntax issues
echo "Lines around admin router:"
awk '/admin/{print NR ": " $0}' main.py

echo ""
echo "📝 Full main.py content (last 20 lines):"
echo "----------------------------------------"
tail -20 main.py

echo ""
echo "🧪 Quick syntax test:"
python3 -c "
import ast
try:
    with open('main.py', 'r') as f:
        content = f.read()
    ast.parse(content)
    print('✅ main.py syntax is valid')
except SyntaxError as e:
    print(f'❌ Syntax error in main.py:')
    print(f'   Line {e.lineno}: {e.text}')
    print(f'   Error: {e.msg}')
except Exception as e:
    print(f'❌ Error parsing main.py: {e}')
"
