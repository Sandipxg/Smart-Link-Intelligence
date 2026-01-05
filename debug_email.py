import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

def test_smtp():
    print("🔍 DIAGNOSTIC TOOL: Checking Email Configuration...")
    
    # Check 1: Does .env exist?
    if not os.path.exists(".env"):
        print("\n❌ CRITICAL ERROR: '.env' file not found!")
        print("   Solution: authentication credentials must be in a file named '.env'.")
        print("   1. Create a new file named '.env'")
        print("   2. Add your EMAIL_USER and EMAIL_PASS to it.")
        if os.path.exists(".env.example"):
            print("   (I see you have '.env.example' - did you forget to rename it to '.env'?)")
        return

    # Check 2: Load variables
    load_dotenv()
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    
    print(f"   Action: Loaded .env file.")
    
    if not user or "your_email" in user:
        print(f"\n❌ CONFIG ERROR: EMAIL_USER looks invalid or default.")
        print(f"   Current value: {user}")
        print("   Solution: Open .env and put your REAL Gmail address.")
        return
        
    if not password or "your_app_password" in password:
        print(f"\n❌ CONFIG ERROR: EMAIL_PASS looks invalid or default.")
        print("   Solution: Open .env and put your Google App Password.")
        return

    print(f"   User: {user}")
    print(f"   Pass: {'*' * len(password) if password else 'None'}")

    # Check 3: Send Test Email
    print("\n🚀 Attempting to connect to Gmail SMTP...")
    try:
        msg = EmailMessage()
        msg.set_content("This is a test email from your Smart Link Intelligence Debugger.")
        msg["Subject"] = "SMTP Test Success!"
        msg["From"] = user
        msg["To"] = user  # Send to self

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.set_debuglevel(1)  # Show detailed SMTP transaction
            server.starttls()
            print("   ✅ Connected and TLS started.")
            server.login(user, password)
            print("   ✅ Authenticated successfully.")
            server.send_message(msg)
            print("   ✅ Test email sent!")
            
        print("\n🎉 SUCCESS: Email configuration is working perfectly.")
        print("   Check your inbox for the test email.")
        
    except smtplib.SMTPAuthenticationError:
        print("\n❌ AUTHENTICATION ERROR")
        print("   Google rejected your password.")
        print("   Checklist:")
        print("   1. Are you using an **App Password**? (Regular password will NOT work)")
        print("   2. Did you enable 2-Step Verification?")
        print("   3. Are there spaces in the password? (Try removing them)")
    except Exception as e:
        print(f"\n❌ CONNECTION ERROR: {e}")

if __name__ == "__main__":
    test_smtp()
