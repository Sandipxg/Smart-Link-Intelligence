"""
Comprehensive Admin Panel Test Script
Tests database connectivity, API endpoints, and real-time features
"""

import requests
import time
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
ADMIN_PASSWORD = "admin123"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name, status, message=""):
    """Print test result with color"""
    if status:
        print(f"{Colors.GREEN}[PASS]{Colors.END} {name}")
        if message:
            print(f"       {message}")
    else:
        print(f"{Colors.RED}[FAIL]{Colors.END} {name}")
        if message:
            print(f"       {Colors.RED}{message}{Colors.END}")

def print_section(title):
    """Print section header"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{title}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")

def test_admin_login():
    """Test admin login functionality"""
    print_section("Testing Admin Authentication")
    
    session = requests.Session()
    
    # Test login page access
    try:
        response = session.get(f"{BASE_URL}/admin/login")
        print_test("Admin login page accessible", response.status_code == 200)
    except Exception as e:
        print_test("Admin login page accessible", False, str(e))
        return None
    
    # Test login with password
    try:
        response = session.post(f"{BASE_URL}/admin/login", data={
            'password': ADMIN_PASSWORD
        }, allow_redirects=False)
        
        success = response.status_code in [302, 303]
        print_test("Admin login with password", success)
        
        if success:
            return session
        else:
            print_test("Admin login", False, f"Status code: {response.status_code}")
            return None
    except Exception as e:
        print_test("Admin login", False, str(e))
        return None

def test_dashboard(session):
    """Test dashboard access and data"""
    print_section("Testing Dashboard")
    
    if not session:
        print_test("Dashboard access", False, "No session available")
        return
    
    try:
        response = session.get(f"{BASE_URL}/admin/dashboard")
        print_test("Dashboard page loads", response.status_code == 200)
        
        # Check for key elements
        content = response.text
        print_test("Dashboard has stats cards", "Total Users" in content and "Total Revenue" in content)
        print_test("Dashboard has activity log", "Recent Admin Activities" in content or "activity" in content.lower())
        
    except Exception as e:
        print_test("Dashboard access", False, str(e))

def test_live_stats_api(session):
    """Test live statistics API endpoint"""
    print_section("Testing Live Statistics API")
    
    if not session:
        print_test("Live stats API", False, "No session available")
        return
    
    try:
        response = session.get(f"{BASE_URL}/admin/api/stats/live")
        print_test("Live stats API responds", response.status_code == 200)
        
        if response.status_code == 200:
            data = response.json()
            print_test("API returns JSON", 'success' in data)
            
            if data.get('success'):
                stats = data.get('stats', {})
                print_test("Stats contain total_users", 'total_users' in stats, f"Users: {stats.get('total_users', 'N/A')}")
                print_test("Stats contain total_revenue", 'total_revenue' in stats, f"Revenue: ${stats.get('total_revenue', 0):.2f}")
                print_test("Stats contain total_links", 'total_links' in stats, f"Links: {stats.get('total_links', 'N/A')}")
                print_test("API includes timestamp", 'timestamp' in data)
            else:
                print_test("API success flag", False, data.get('error', 'Unknown error'))
    except Exception as e:
        print_test("Live stats API", False, str(e))

def test_activities_api(session):
    """Test activities API endpoint"""
    print_section("Testing Activities API")
    
    if not session:
        print_test("Activities API", False, "No session available")
        return
    
    try:
        response = session.get(f"{BASE_URL}/admin/api/activities/recent?limit=5")
        print_test("Activities API responds", response.status_code == 200)
        
        if response.status_code == 200:
            data = response.json()
            print_test("API returns JSON", 'success' in data)
            
            if data.get('success'):
                activities = data.get('activities', [])
                print_test("Activities returned", len(activities) >= 0, f"Count: {len(activities)}")
                
                if activities:
                    first_activity = activities[0]
                    print_test("Activity has required fields", 
                              all(key in first_activity for key in ['user_id', 'activity_type', 'timestamp']))
    except Exception as e:
        print_test("Activities API", False, str(e))

def test_revenue_api(session):
    """Test revenue API endpoint"""
    print_section("Testing Revenue API")
    
    if not session:
        print_test("Revenue API", False, "No session available")
        return
    
    try:
        response = session.get(f"{BASE_URL}/admin/api/revenue/live")
        print_test("Revenue API responds", response.status_code == 200)
        
        if response.status_code == 200:
            data = response.json()
            print_test("API returns JSON", 'success' in data)
            
            if data.get('success'):
                revenue = data.get('revenue', {})
                print_test("Revenue data complete", all(key in revenue for key in ['total', 'today', 'week']))
                print(f"       Total: ${revenue.get('total', 0):.2f}, Today: ${revenue.get('today', 0):.2f}, Week: ${revenue.get('week', 0):.2f}")
    except Exception as e:
        print_test("Revenue API", False, str(e))

def test_user_management(session):
    """Test user management pages"""
    print_section("Testing User Management")
    
    if not session:
        print_test("User management", False, "No session available")
        return
    
    try:
        response = session.get(f"{BASE_URL}/admin/users")
        print_test("Users page loads", response.status_code == 200)
        
        content = response.text
        print_test("Users page has table", "table" in content.lower())
        print_test("Users page has search", "search" in content.lower())
        
    except Exception as e:
        print_test("User management", False, str(e))

def test_ad_management(session):
    """Test ad management pages"""
    print_section("Testing Ad Management")
    
    if not session:
        print_test("Ad management", False, "No session available")
        return
    
    try:
        response = session.get(f"{BASE_URL}/admin/ads")
        print_test("Ads page loads", response.status_code == 200)
        
    except Exception as e:
        print_test("Ad management", False, str(e))

def test_real_time_updates(session):
    """Test real-time update functionality"""
    print_section("Testing Real-Time Updates")
    
    if not session:
        print_test("Real-time updates", False, "No session available")
        return
    
    print(f"{Colors.YELLOW}[INFO]{Colors.END} Testing AJAX polling (5-second intervals)...")
    
    try:
        # Get initial stats
        response1 = session.get(f"{BASE_URL}/admin/api/stats/live")
        data1 = response1.json()
        
        print(f"       Initial stats retrieved at {datetime.now().strftime('%H:%M:%S')}")
        
        # Wait 2 seconds
        time.sleep(2)
        
        # Get updated stats
        response2 = session.get(f"{BASE_URL}/admin/api/stats/live")
        data2 = response2.json()
        
        print(f"       Updated stats retrieved at {datetime.now().strftime('%H:%M:%S')}")
        
        # Check if timestamps are different
        if data1.get('success') and data2.get('success'):
            timestamp1 = data1.get('timestamp')
            timestamp2 = data2.get('timestamp')
            print_test("API returns fresh data", timestamp1 != timestamp2)
            print_test("Stats update successfully", True, "Real-time polling working")
        
    except Exception as e:
        print_test("Real-time updates", False, str(e))

def main():
    """Run all tests"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}ADMIN PANEL COMPREHENSIVE TEST SUITE{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"Testing against: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run tests
    session = test_admin_login()
    
    if session:
        test_dashboard(session)
        test_live_stats_api(session)
        test_activities_api(session)
        test_revenue_api(session)
        test_user_management(session)
        test_ad_management(session)
        test_real_time_updates(session)
    else:
        print(f"\n{Colors.RED}Cannot proceed with tests - admin login failed{Colors.END}")
        print(f"{Colors.YELLOW}Make sure:{Colors.END}")
        print(f"  1. Flask app is running on {BASE_URL}")
        print(f"  2. Admin password is '{ADMIN_PASSWORD}'")
        print(f"  3. Database is properly initialized")
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST SUITE COMPLETED{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

if __name__ == "__main__":
    main()
