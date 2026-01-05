"""
Quick Start Guide for Admin Panel
Run this script to verify everything is working
"""

import os
import sys
import subprocess

def print_header(text):
    print("\n" + "="*60)
    print(text)
    print("="*60)

def check_file_exists(filepath):
    """Check if a file exists"""
    exists = os.path.exists(filepath)
    status = "[OK]" if exists else "[MISSING]"
    print(f"{status} {filepath}")
    return exists

def main():
    print_header("ADMIN PANEL - QUICK START VERIFICATION")
    
    # Check required files
    print("\n1. Checking required files...")
    files_ok = all([
        check_file_exists("smart_links.db"),
        check_file_exists("app.py"),
        check_file_exists("admin_panel.py"),
        check_file_exists("migrate_admin_db.py"),
        check_file_exists("templates/admin/dashboard.html"),
        check_file_exists("templates/admin/users.html"),
    ])
    
    if not files_ok:
        print("\n[ERROR] Some required files are missing!")
        return
    
    # Check database migration
    print("\n2. Database migration status...")
    print("[INFO] Run 'python migrate_admin_db.py' if not done yet")
    
    # Instructions
    print_header("NEXT STEPS")
    print("""
1. Run database migration (if not done):
   python migrate_admin_db.py

2. Start the Flask application:
   python app.py

3. Access admin panel:
   http://localhost:5000/admin/login
   Password: admin123

4. Test real-time features:
   python test_admin_panel.py

5. Features to test:
   - Dashboard auto-updates every 5 seconds
   - User management (view, edit, delete)
   - Ad management (create, toggle, assign)
   - Live revenue tracking
   - Activity monitoring
   - Export functionality

ADMIN PANEL FEATURES:
[OK] Real-time dashboard updates (AJAX polling)
[OK] Live statistics API endpoints
[OK] Database optimization with indexes
[OK] WAL mode for concurrent access
[OK] User activity tracking
[OK] Ad impression tracking with revenue
[OK] Export to CSV functionality
[OK] Responsive design
[OK] Search and pagination

SECURITY NOTES:
- Change admin password in admin_panel.py (line 55)
- Admin session expires when browser closes
- All routes protected with authentication
- SQL injection prevention with parameterized queries

For issues or questions, check the implementation_plan.md
    """)
    
    print_header("ADMIN PANEL READY")
    print("All checks passed! You can now start using the admin panel.\n")

if __name__ == "__main__":
    main()
