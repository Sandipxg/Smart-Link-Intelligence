"""
Test WhatsApp referrer detection from User-Agent strings
"""

def test_whatsapp_user_agents():
    """Test various WhatsApp User-Agent strings"""
    
    # Real WhatsApp User-Agent examples
    test_cases = [
        # Android WhatsApp
        ("WhatsApp/2.23.20.0 A", "WhatsApp"),
        ("Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 WhatsApp/2.21.15.15", "WhatsApp"),
        
        # iOS WhatsApp
        ("WhatsApp/2.23.1 iOS/16.0", "WhatsApp"),
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) WhatsApp/23.1.78", "WhatsApp"),
        
        # WhatsApp Business
        ("WhatsApp Business/2.23.20.0", "WhatsApp"),
        
        # Regular browsers (should be "no referrer" -> Direct)
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0", "no referrer"),
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) Safari/604.1", "no referrer"),
        
        # Instagram
        ("Instagram 250.0.0.0.0 Android", "Instagram"),
        
        # Facebook
        ("Mozilla/5.0 (Linux; Android 10) FBAN/FB4A FBAV/350.0.0.0", "Facebook"),
    ]
    
    def detect_referrer_from_ua(user_agent, header_referrer="no referrer"):
        """Simulate the referrer detection logic"""
        referrer = header_referrer
        
        if not referrer or referrer == 'no referrer':
            ua_lower = user_agent.lower()
            if 'whatsapp' in ua_lower:
                referrer = 'WhatsApp'
            elif 'instagram' in ua_lower:
                referrer = 'Instagram'
            elif any(x in ua_lower for x in ['fban', 'fbav']):
                referrer = 'Facebook'
        
        return referrer
    
    print("=" * 80)
    print("WHATSAPP USER-AGENT DETECTION TEST")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for user_agent, expected in test_cases:
        result = detect_referrer_from_ua(user_agent)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status}")
        print(f"  User-Agent: {user_agent[:70]}...")
        print(f"  Expected: {expected}")
        print(f"  Got: {result}")
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = test_whatsapp_user_agents()
    
    print("\n" + "=" * 80)
    print("IMPORTANT NOTES:")
    print("=" * 80)
    print("1. WhatsApp detection works via User-Agent string")
    print("2. If showing 'Direct', the User-Agent might not contain 'whatsapp'")
    print("3. Check referrer_debug.txt after clicking to see actual User-Agent")
    print("4. Some WhatsApp versions use in-app browser without 'whatsapp' in UA")
    print("5. Consider using ?ref=whatsapp parameter for guaranteed tracking")
    
    exit(0 if success else 1)
