#!/usr/bin/env python3
"""
Test script to verify the analytics page loads without JSON serialization errors
"""

import requests
import time

def test_admin_analytics():
    """Test admin analytics page"""
    base_url = "http://127.0.0.1:5000"
    
    # Wait for server to be ready
    print("Waiting for server to be ready...")
    time.sleep(3)
    
    try:
        # Test admin login page
        print("Testing admin login page...")
        response = requests.get(f"{base_url}/admin/login", timeout=10)
        if response.status_code == 200:
            print("✓ Admin login page loads successfully")
        else:
            print(f"✗ Admin login page failed: {response.status_code}")
            return False
        
        # Test admin login
        print("Testing admin login...")
        login_data = {"password": "admin123"}
        session = requests.Session()
        response = session.post(f"{base_url}/admin/login", data=login_data, timeout=10)
        
        if response.status_code == 200 and "Welcome to Admin Panel" in response.text:
            print("✓ Admin login successful")
        else:
            print(f"✗ Admin login failed: {response.status_code}")
            return False
        
        # Test analytics page (this was causing the JSON serialization error)
        print("Testing analytics page...")
        response = session.get(f"{base_url}/admin/analytics", timeout=10)
        
        if response.status_code == 200:
            print("✓ Analytics page loads successfully")
            
            # Check if the page contains expected elements
            if "Revenue Analytics" in response.text:
                print("✓ Analytics page contains expected content")
            else:
                print("✗ Analytics page missing expected content")
                return False
                
            # Check if JavaScript charts are present
            if "revenueChart" in response.text and "Chart.js" in response.text:
                print("✓ Analytics page contains chart JavaScript")
            else:
                print("✗ Analytics page missing chart JavaScript")
                return False
                
        else:
            print(f"✗ Analytics page failed: {response.status_code}")
            return False
        
        # Test other admin pages
        pages_to_test = [
            ("/admin/dashboard", "Admin Dashboard"),
            ("/admin/users", "User Management"),
            ("/admin/ads", "Ad Management"),
            ("/admin/activity", "User Activity")
        ]
        
        for url, expected_content in pages_to_test:
            print(f"Testing {url}...")
            response = session.get(f"{base_url}{url}", timeout=10)
            if response.status_code == 200 and expected_content in response.text:
                print(f"✓ {url} loads successfully")
            else:
                print(f"✗ {url} failed: {response.status_code}")
                return False
        
        print("\n🎉 All admin panel tests passed! JSON serialization issue appears to be fixed.")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Request error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_admin_analytics()
    if success:
        print("\n✅ Admin panel is working correctly!")
    else:
        print("\n❌ Admin panel has issues that need to be addressed.")