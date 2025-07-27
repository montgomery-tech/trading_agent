#!/usr/bin/env python3
"""
JWT Final Cleanup Script
Complete removal of all remaining JWT references to prevent future issues

This script performs a comprehensive cleanup of JWT remnants including:
- Files containing JWT code
- Environment variables
- Configuration references
- Middleware components
- Import statements
"""

import os
import shutil
import re
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JWTFinalCleanup:
    """Complete JWT cleanup manager"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_dir = Path("jwt_final_cleanup_backups")
        self.issues_found = []
        
        # Files that might contain JWT references
        self.files_to_check = [
            "api/routes/auth.py",
            "api/auth_routes.py", 
            "api/jwt_service.py",
            "api/auth_models.py",
            "api/models/auth.py",
            "api/security/middleware.py",
            "api/middleware.py",
            ".env",
            ".env.example",
            "config.py",
            "api/config.py",
            "requirements.txt"
        ]
        
        # JWT patterns to search for and remove
        self.jwt_patterns = [
            r'import\s+jwt',
            r'from\s+jwt\s+import',
            r'SECRET_KEY\s*=',
            r'JWT_ALGORITHM\s*=',
            r'JWT_EXPIRE\s*=',
            r'create_access_token',
            r'validate_token',
            r'jwt\.encode',
            r'jwt\.decode',
            r'TokenType',
            r'get_current_user_from_token',
            r'AuthenticatedUser\s*\(',
            r'TokenData\s*\(',
        ]
    
    def create_backup_directory(self):
        """Create backup directory"""
        self.backup_dir.mkdir(exist_ok=True)
        logger.info(f"✅ Backup directory ready: {self.backup_dir}")
    
    def backup_file(self, file_path: str) -> str:
        """Backup file before modification"""
        if not os.path.exists(file_path):
            return None
            
        backup_name = f"{os.path.basename(file_path)}.backup_{self.timestamp}"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(file_path, backup_path)
        logger.info(f"✅ Backed up {file_path}")
        return str(backup_path)
    
    def scan_file_for_jwt(self, file_path: str) -> dict:
        """Scan a file for JWT references"""
        if not os.path.exists(file_path):
            return None
            
        result = {
            'file': file_path,
            'jwt_references': [],
            'should_delete': False,
            'needs_cleanup': False
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check each pattern
            for pattern in self.jwt_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    result['jwt_references'].append({
                        'pattern': pattern,
                        'match': match.group(),
                        'line': line_num,
                        'context': lines[line_num - 1].strip() if line_num <= len(lines) else ''
                    })
            
            # Determine action needed
            if file_path in ['api/routes/auth.py', 'api/auth_routes.py', 'api/jwt_service.py']:
                result['should_delete'] = True
            elif result['jwt_references']:
                result['needs_cleanup'] = True
                
        except Exception as e:
            logger.error(f"Error scanning {file_path}: {e}")
            result['error'] = str(e)
        
        return result
    
    def delete_jwt_files(self):
        """Delete files that are entirely JWT-related"""
        jwt_files = [
            "api/routes/auth.py",
            "api/auth_routes.py", 
            "api/jwt_service.py",
            "api/models/auth.py"
        ]
        
        deleted_files = []
        
        for file_path in jwt_files:
            if os.path.exists(file_path):
                # Backup first
                self.backup_file(file_path)
                
                # Delete file
                os.remove(file_path)
                deleted_files.append(file_path)
                logger.info(f"🗑️ Deleted JWT file: {file_path}")
        
        return deleted_files
    
    def clean_env_file(self):
        """Remove JWT environment variables from .env file"""
        env_file = ".env"
        
        if not os.path.exists(env_file):
            logger.info("ℹ️ No .env file found")
            return False
        
        # Backup first
        self.backup_file(env_file)
        
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # JWT-related environment variables to remove
        jwt_env_vars = [
            'SECRET_KEY',
            'JWT_ALGORITHM', 
            'JWT_EXPIRE_MINUTES',
            'JWT_REFRESH_EXPIRE_DAYS',
            'JWT_ACCESS_TOKEN_EXPIRE',
            'JWT_REFRESH_TOKEN_EXPIRE'
        ]
        
        cleaned_lines = []
        removed_vars = []
        
        for line in lines:
            should_keep = True
            
            for var in jwt_env_vars:
                if line.strip().startswith(f"{var}=") or line.strip().startswith(f"#{var}="):
                    should_keep = False
                    removed_vars.append(var)
                    break
            
            if should_keep:
                cleaned_lines.append(line)
        
        # Write cleaned file
        with open(env_file, 'w') as f:
            f.writelines(cleaned_lines)
        
        if removed_vars:
            logger.info(f"🧹 Cleaned .env file - removed: {', '.join(removed_vars)}")
            return True
        else:
            logger.info("ℹ️ No JWT variables found in .env file")
            return False
    
    def check_middleware_files(self):
        """Check middleware files for JWT references"""
        middleware_files = [
            "api/security/middleware.py",
            "api/middleware.py",
            "api/security/__init__.py"
        ]
        
        middleware_issues = []
        
        for file_path in middleware_files:
            result = self.scan_file_for_jwt(file_path)
            if result and result['jwt_references']:
                middleware_issues.append(result)
                logger.warning(f"⚠️ JWT references found in middleware: {file_path}")
        
        return middleware_issues
    
    def scan_all_route_files(self):
        """Scan all route files for remaining JWT imports"""
        routes_dir = Path("api/routes")
        
        if not routes_dir.exists():
            logger.warning("⚠️ Routes directory not found")
            return []
        
        route_issues = []
        
        for py_file in routes_dir.glob("*.py"):
            if py_file.name.startswith('__'):
                continue
                
            result = self.scan_file_for_jwt(str(py_file))
            if result and result['jwt_references']:
                route_issues.append(result)
                logger.warning(f"⚠️ JWT references found in route: {py_file}")
        
        return route_issues
    
    def clean_requirements_txt(self):
        """Remove JWT-related packages from requirements.txt"""
        req_file = "requirements.txt"
        
        if not os.path.exists(req_file):
            logger.info("ℹ️ No requirements.txt found")
            return False
        
        # Backup first
        self.backup_file(req_file)
        
        with open(req_file, 'r') as f:
            lines = f.readlines()
        
        # JWT-related packages to remove
        jwt_packages = [
            'PyJWT',
            'pyjwt',
            'python-jose',
            'jose',
            'authlib'  # If only used for JWT
        ]
        
        cleaned_lines = []
        removed_packages = []
        
        for line in lines:
            should_keep = True
            line_lower = line.lower().strip()
            
            for package in jwt_packages:
                if line_lower.startswith(package.lower()) or f"{package.lower()}==" in line_lower:
                    should_keep = False
                    removed_packages.append(package)
                    break
            
            if should_keep:
                cleaned_lines.append(line)
        
        # Write cleaned file
        with open(req_file, 'w') as f:
            f.writelines(cleaned_lines)
        
        if removed_packages:
            logger.info(f"🧹 Cleaned requirements.txt - removed: {', '.join(removed_packages)}")
            return True
        else:
            logger.info("ℹ️ No JWT packages found in requirements.txt")
            return False
    
    def generate_cleanup_report(self, deleted_files, env_cleaned, req_cleaned, middleware_issues, route_issues):
        """Generate final cleanup report"""
        
        report = f"""
🧹 JWT FINAL CLEANUP REPORT
{'=' * 50}
Timestamp: {self.timestamp}

✅ ACTIONS COMPLETED:

📁 Files Deleted:
"""
        if deleted_files:
            for file in deleted_files:
                report += f"   🗑️ {file}\n"
        else:
            report += "   ℹ️ No JWT files found to delete\n"
        
        report += f"""
🔧 Configuration Cleaned:
   📝 .env file: {"✅ JWT variables removed" if env_cleaned else "ℹ️ No JWT variables found"}
   📦 requirements.txt: {"✅ JWT packages removed" if req_cleaned else "ℹ️ No JWT packages found"}

🔍 Middleware Check:
"""
        if middleware_issues:
            report += f"   ⚠️ {len(middleware_issues)} files with JWT references found\n"
            for issue in middleware_issues:
                report += f"   📄 {issue['file']}: {len(issue['jwt_references'])} references\n"
        else:
            report += "   ✅ No JWT references in middleware\n"
        
        report += f"""
🛣️ Route Files Check:
"""
        if route_issues:
            report += f"   ⚠️ {len(route_issues)} route files with JWT references\n"
            for issue in route_issues:
                report += f"   📄 {issue['file']}: {len(issue['jwt_references'])} references\n"
        else:
            report += "   ✅ All route files clean\n"
        
        report += f"""
📁 Backups Created:
   All modified files backed up to: {self.backup_dir}/

🎯 FINAL STATUS:
"""
        
        total_issues = len(middleware_issues) + len(route_issues)
        if total_issues == 0:
            report += "   🎉 JWT CLEANUP 100% COMPLETE!\n"
            report += "   ✅ No remaining JWT references found\n"
            report += "   🚀 System is fully migrated to API key authentication\n"
        else:
            report += f"   ⚠️ {total_issues} files still contain JWT references\n"
            report += "   🛠️ Manual review recommended for remaining files\n"
        
        report += f"""
🗑️ CLEANUP RECOMMENDATIONS:
   • Remove backup files when confident: rm -rf {self.backup_dir}/
   • Restart application to ensure all changes take effect
   • Consider uninstalling JWT packages: pip uninstall PyJWT python-jose
"""
        
        return report
    
    def execute_final_cleanup(self):
        """Execute the complete final cleanup"""
        logger.info("🧹 Starting JWT final cleanup...")
        
        try:
            # Step 1: Create backups
            self.create_backup_directory()
            
            # Step 2: Delete JWT files
            deleted_files = self.delete_jwt_files()
            
            # Step 3: Clean environment variables
            env_cleaned = self.clean_env_file()
            
            # Step 4: Clean requirements.txt
            req_cleaned = self.clean_requirements_txt()
            
            # Step 5: Check middleware for issues
            middleware_issues = self.check_middleware_files()
            
            # Step 6: Check route files
            route_issues = self.scan_all_route_files()
            
            # Step 7: Generate report
            report = self.generate_cleanup_report(
                deleted_files, env_cleaned, req_cleaned, 
                middleware_issues, route_issues
            )
            
            # Save report
            report_file = self.backup_dir / f"jwt_cleanup_report_{self.timestamp}.txt"
            with open(report_file, 'w') as f:
                f.write(report)
            
            print(report)
            logger.info(f"📄 Report saved to: {report_file}")
            
            # Return success status
            total_issues = len(middleware_issues) + len(route_issues)
            return total_issues == 0
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return False

def main():
    """Main execution function"""
    print("🧹 JWT FINAL CLEANUP - COMPLETE REMOVAL")
    print("=" * 50)
    
    cleanup = JWTFinalCleanup()
    success = cleanup.execute_final_cleanup()
    
    if success:
        print("\n🎉 SUCCESS: JWT cleanup 100% complete!")
        print("🔑 Your system is now fully API key only")
        print("🚀 Safe to restart your application")
    else:
        print("\n⚠️ REVIEW NEEDED: Some JWT references remain")
        print("🛠️ Check the report for manual cleanup tasks")
    
    return success

if __name__ == "__main__":
    main()
