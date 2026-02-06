import os
import smtplib
from config import FLASK_CONFIG
from utils import send_email

def verify_config():
    print("--- Verifying Email Configuration ---")
    
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    
    if email_user:
        print(f"✅ EMAIL_USER found: {email_user}")
    else:
        print("❌ EMAIL_USER NOT found in environment variables")
        
    if email_pass:
        print(f"✅ EMAIL_PASS found: {'*' * len(email_pass)} (masked)")
    else:
        print("❌ EMAIL_PASS NOT found in environment variables")
        
    print("\n--- Trying SMTP Connection (Dry Run) ---")
    if email_user and email_pass:
        try:
            print("Connecting to smtp.gmail.com...")
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            print("Attempting login...")
            server.login(email_user, email_pass)
            print("✅ Login Successful! Credentials are valid.")
            server.quit()
        except Exception as e:
            print(f"❌ Login Failed: {e}")
    else:
        print("Skipping SMTP check due to missing credentials.")

if __name__ == "__main__":
    verify_config()
