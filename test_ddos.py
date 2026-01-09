import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Configuration
BASE_URL = "http://127.0.0.1:5000"
# Replace with a valid link code from your database
TARGET_LINK = "r/demo123" 

def test_single_user_burst():
    """Test 1: Single IP sending requests too fast (Burst/Suspicious)"""
    print(f"\n[Test 1] Starting Burst Test on {BASE_URL}/{TARGET_LINK}...")
    
    url = f"{BASE_URL}/{TARGET_LINK}"
    success = 0
    blocked = 0
    
    def send_request():
        nonlocal success, blocked
        try:
            # Short timeout to send fast
            r = requests.get(url, timeout=2)
            if "ddos_blocked" in r.text or r.status_code == 429:
                blocked += 1
                return "BLOCKED"
            else:
                success += 1
                return "OK"
        except:
            return "ERROR"

    # Send 60 requests in < 5 seconds
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(lambda _: send_request(), range(60)))
        
    print(f"Results: {success} Passed, {blocked} Blocked/Protected")
    if blocked > 0:
        print("✅ SUCCESS: Protection kicked in!")
    else:
        print("⚠️ WARNING: No protection triggered (Check thresholds)")

def test_distributed_attack():
    """Test 2: Multiple Fake IPs (Simulating Botnet)"""
    print(f"\n[Test 2] Starting Distributed Attack Simulation...")
    
    url = f"{BASE_URL}/{TARGET_LINK}"
    
    def send_fake_ip_request(i):
        fake_ip = f"10.0.0.{i}"
        headers = {
            "X-Forwarded-For": fake_ip,
            "User-Agent": f"Botnet-Agent-{i}"
        }
        try:
            r = requests.get(url, headers=headers, timeout=2)
            print(f"IP {fake_ip}: {r.status_code}")
        except:
            pass

    # Send 50 requests from 50 different "IPs"
    # This tests the 'More than 50 new users' scenario you fixed
    # These should ALL be allowed now (not suspicious)
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(send_fake_ip_request, range(1, 55))
        
    print("Test 2 Complete. Check server logs. These should mostly be ALLOWED now.")

if __name__ == "__main__":
    print("DDoS Protection Test Tool")
    print("=========================")
    print("Make sure your app is running on port 5000")
    
    # Needs a real link code to test effectively
    code = input("Enter a valid Link Code to test (e.g. AbC12s): ")
    TARGET_LINK = f"r/{code}"
    
    print("\n1. Test Single User Burst (Should Block)")
    print("2. Test Multi-User Traffic (Should Allow)")
    choice = input("Select test (1/2): ")
    
    if choice == "1":
        test_single_user_burst()
    elif choice == "2":
        test_distributed_attack()
    else:
        print("Invalid choice")
