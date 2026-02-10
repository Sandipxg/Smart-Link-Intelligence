"""
Quick localhost testing script
Simulates clicks from different referrers
"""
import requests
import time

BASE_URL = "http://127.0.0.1:5000"

def test_link_clicks(link_code):
    """Test clicking a link with different referrers"""
    
    print("=" * 80)
    print(f"TESTING LINK: {link_code}")
    print("=" * 80)
    
    test_cases = [
        ("Direct (no referrer)", f"{BASE_URL}/r/{link_code}"),
        ("WhatsApp", f"{BASE_URL}/r/{link_code}?ref=whatsapp"),
        ("Facebook", f"{BASE_URL}/r/{link_code}?ref=facebook"),
        ("Twitter", f"{BASE_URL}/r/{link_code}?ref=twitter"),
        ("Gmail", f"{BASE_URL}/r/{link_code}?ref=gmail"),
        ("LinkedIn", f"{BASE_URL}/r/{link_code}?ref=linkedin"),
    ]
    
    print("\nSimulating clicks from different sources...\n")
    
    for i, (source, url) in enumerate(test_cases, 1):
        try:
            print(f"{i}. Clicking from {source}...")
            response = requests.get(url, allow_redirects=False)
            
            if response.status_code in [301, 302, 303, 307, 308]:
                print(f"   ✅ Redirected successfully (Status: {response.status_code})")
            else:
                print(f"   ⚠️  Unexpected status: {response.status_code}")
            
            # Wait 2 seconds between clicks to avoid rate limiting
            time.sleep(2)
            
        except requests.exceptions.ConnectionError:
            print(f"   ❌ ERROR: Flask app not running!")
            print(f"   → Start it with: python app.py")
            return False
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            return False
    
    print("\n" + "=" * 80)
    print("✅ ALL CLICKS COMPLETED")
    print("=" * 80)
    print(f"\nNow check analytics:")
    print(f"→ {BASE_URL}/links/{link_code}")
    print("\nExpected results:")
    print("  - Total Clicks: 6")
    print("  - Unique Visitors: 1 (you)")
    print("  - Referrer Graph:")
    print("    • Direct: 1")
    print("    • WhatsApp: 1")
    print("    • Facebook: 1")
    print("    • Twitter: 1")
    print("    • Gmail: 1")
    print("    • LinkedIn: 1")
    print("=" * 80)
    
    return True

def test_duplicate_prevention(link_code):
    """Test duplicate click prevention"""
    
    print("\n" + "=" * 80)
    print("TESTING DUPLICATE PREVENTION")
    print("=" * 80)
    
    url = f"{BASE_URL}/r/{link_code}?ref=test_dup"
    
    try:
        print("\n1. First click...")
        response1 = requests.get(url, allow_redirects=False)
        print(f"   ✅ Status: {response1.status_code}")
        
        print("\n2. Second click (within 5 seconds)...")
        time.sleep(2)
        response2 = requests.get(url, allow_redirects=False)
        print(f"   ✅ Status: {response2.status_code}")
        
        print("\n3. Waiting 12 seconds...")
        time.sleep(12)
        
        print("\n4. Third click (after 12 seconds)...")
        response3 = requests.get(url, allow_redirects=False)
        print(f"   ✅ Status: {response3.status_code}")
        
        print("\n" + "=" * 80)
        print("✅ DUPLICATE TEST COMPLETED")
        print("=" * 80)
        print(f"\nCheck analytics: {BASE_URL}/links/{link_code}")
        print("\nExpected results:")
        print("  - Click 1: Logged ✅")
        print("  - Click 2: Blocked (duplicate within 10s) ❌")
        print("  - Click 3: Logged (after 10s) ✅")
        print("  - Total: 2 clicks (not 3)")
        print("=" * 80)
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"   ❌ ERROR: Flask app not running!")
        print(f"   → Start it with: python app.py")
        return False
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("LOCALHOST TESTING SCRIPT")
    print("=" * 80)
    print("\nThis script will test:")
    print("  1. Referrer tracking from different sources")
    print("  2. Duplicate click prevention")
    print("\nMake sure your Flask app is running: python app.py")
    print("=" * 80)
    
    link_code = input("\nEnter your link code (e.g., test123): ").strip()
    
    if not link_code:
        print("❌ No link code provided!")
        exit(1)
    
    print(f"\n🚀 Starting tests for link: {link_code}\n")
    
    # Test 1: Different referrers
    success1 = test_link_clicks(link_code)
    
    if success1:
        # Test 2: Duplicate prevention
        input("\nPress Enter to test duplicate prevention...")
        success2 = test_duplicate_prevention(link_code)
        
        if success2:
            print("\n" + "=" * 80)
            print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print("\nNext steps:")
            print("  1. Open analytics page in browser")
            print("  2. Verify referrer graph shows correct distribution")
            print("  3. Verify no duplicate clicks")
            print("=" * 80)
