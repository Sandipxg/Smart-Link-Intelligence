"""
Test script to verify referrer tracking for all platforms
Tests: Gmail, Facebook, WhatsApp, Twitter, LinkedIn, YouTube, Google, Direct, Other
"""

def test_referrer_classification():
    """Test the referrer classification logic"""
    from urllib.parse import urlparse
    
    # Test cases: (input_referrer, expected_category)
    test_cases = [
        # Direct traffic
        ("", "Direct"),
        ("no referrer", "Direct"),
        ("None", "Direct"),
        (None, "Direct"),
        
        # Smart Tracking codes (plain text)
        ("whatsapp", "WhatsApp"),
        ("wa", "WhatsApp"),
        ("w", "WhatsApp"),
        ("gmail", "Gmail"),
        ("mail", "Gmail"),
        ("facebook", "Facebook"),
        ("fb", "Facebook"),
        ("twitter", "Twitter"),
        ("x", "Twitter"),
        ("linkedin", "LinkedIn"),
        ("li", "LinkedIn"),
        ("youtube", "YouTube"),
        ("yt", "YouTube"),
        
        # URL-based referrers
        ("https://mail.google.com/mail/u/0/", "Gmail"),
        ("https://www.google.com/search?q=test", "Google"),
        ("https://google.co.in/", "Google"),
        ("https://www.facebook.com/", "Facebook"),
        ("https://fb.com/", "Facebook"),
        ("https://www.instagram.com/", "Facebook"),
        ("https://l.instagram.com/?u=https://example.com", "Facebook"),
        ("https://whatsapp.com/", "WhatsApp"),
        ("https://wa.me/1234567890", "WhatsApp"),
        ("https://t.co/abc123", "Twitter"),
        ("https://twitter.com/user/status/123", "Twitter"),
        ("https://x.com/user/status/123", "Twitter"),
        ("https://www.linkedin.com/feed/", "LinkedIn"),
        ("https://lnkd.in/abc123", "LinkedIn"),
        ("https://www.youtube.com/watch?v=abc", "YouTube"),
        ("https://youtu.be/abc123", "YouTube"),
        
        # Other sources
        ("https://reddit.com/r/test", "Other"),
        ("https://example.com/page", "Other"),
        ("https://news.ycombinator.com/", "Other"),
    ]
    
    def classify_referrer(ref_raw):
        """Replicate the classification logic from links.py"""
        if not ref_raw or ref_raw == 'no referrer' or ref_raw == 'None':
            return "Direct"
        
        try:
            ref_lower = ref_raw.lower()
            
            # Check for Smart Tracking codes or plain text first
            if ref_lower in ['whatsapp', 'wa', 'w']:
                return "WhatsApp"
            if ref_lower in ['gmail', 'mail']:
                return "Gmail"
            if ref_lower in ['facebook', 'fb']:
                return "Facebook"
            if ref_lower in ['twitter', 'x']:
                return "Twitter"
            if ref_lower in ['linkedin', 'li']:
                return "LinkedIn"
            if ref_lower in ['youtube', 'yt']:
                return "YouTube"
            
            # Fallback to URL parsing
            if not ref_raw.startswith(('http://', 'https://')):
                temp_url = 'http://' + ref_raw
            else:
                temp_url = ref_raw
            
            domain = urlparse(temp_url).netloc.lower()
            if not domain:
                domain = ref_lower
            
            if 'mail.google.com' in domain:
                return "Gmail"
            elif 'google.' in domain:
                return "Google"
            elif any(x in domain for x in ['facebook.com', 'fb.com', 'instagram.com']):
                return "Facebook"
            elif any(x in domain for x in ['whatsapp.com', 'wa.me']):
                return "WhatsApp"
            elif domain == 't.co' or 'twitter.com' in domain or 'x.com' in domain:
                return "Twitter"
            elif any(x in domain for x in ['linkedin.com', 'lnkd.in']):
                return "LinkedIn"
            elif any(x in domain for x in ['youtube.com', 'youtu.be']):
                return "YouTube"
            else:
                return "Other"
        except Exception as e:
            print(f"Error parsing referrer '{ref_raw}': {e}")
            return "Other"
    
    # Run tests
    print("=" * 80)
    print("REFERRER CLASSIFICATION TEST RESULTS")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for input_ref, expected in test_cases:
        result = classify_referrer(input_ref)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        # Format input for display
        display_input = f"'{input_ref}'" if input_ref else "None/Empty"
        
        print(f"{status} | Input: {display_input:<50} | Expected: {expected:<10} | Got: {result:<10}")
    
    print("=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    # Test all categories are present
    print("\nVERIFYING ALL CATEGORIES:")
    all_categories = ["Direct", "Gmail", "Google", "Facebook", "WhatsApp", "Twitter", "LinkedIn", "YouTube", "Other"]
    tested_categories = set(expected for _, expected in test_cases)
    
    for category in all_categories:
        if category in tested_categories:
            print(f"✓ {category} - Tested")
        else:
            print(f"✗ {category} - NOT TESTED")
    
    return failed == 0

if __name__ == "__main__":
    success = test_referrer_classification()
    exit(0 if success else 1)
