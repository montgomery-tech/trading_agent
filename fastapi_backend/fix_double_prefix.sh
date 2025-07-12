#!/bin/bash

# =============================================================================
# Fix Double Prefix Issue in main.py
# Removes the duplicate prefix that's causing /api/v1/admin/api/v1/admin/users
# =============================================================================

echo "🔧 Fixing Double Prefix Issue in main.py"
echo "========================================"

# Create backup
cp main.py main.py.backup.$(date +%Y%m%d_%H%M%S)
echo "📦 Created backup of main.py"

# Show current problem
echo ""
echo "❌ Current problematic lines:"
grep -n -A 4 -B 1 "admin.router" main.py

# Fix the issue using sed
echo ""
echo "🔧 Applying fix..."

# Method 1: Replace the entire admin router inclusion block
sed -i.tmp '/# Include admin routes/,/tags=\["Admin"\]/c\
# Include admin routes\
app.include_router(admin.router)' main.py

echo "✅ Applied fix to main.py"

# Verify the fix
echo ""
echo "✅ Fixed lines:"
grep -n -A 2 -B 1 "admin.router" main.py

# Clean up temp file
rm -f main.py.tmp

echo ""
echo "🎯 Summary of fix:"
echo "  BEFORE: app.include_router(admin.router, prefix=f\"{settings.API_V1_PREFIX}/admin\", tags=[\"Admin\"])"
echo "  AFTER:  app.include_router(admin.router)"
echo ""
echo "This removes the double prefix issue that was creating:"
echo "  /api/v1/admin/api/v1/admin/users (wrong)"
echo ""
echo "Now it will create:"
echo "  /api/v1/admin/users (correct)"
echo ""
echo "🚀 Next step: Restart your server!"
echo "   kill \$(lsof -t -i:8000)"
echo "   python3 main.py"
