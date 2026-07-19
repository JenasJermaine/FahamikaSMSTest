import os
import africastalking as at

AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY = os.getenv("AT_API_KEY")
TEST_SMS_RECIPIENT = os.getenv("TEST_SMS_RECIPIENT")

if not AT_API_KEY:
    raise ValueError("Missing environment variable: AT_API_KEY")

if not TEST_SMS_RECIPIENT:
    raise ValueError("Missing environment variable: TEST_SMS_RECIPIENT")

at.initialize(
    username=AT_USERNAME,       # <-- ALWAYS "sandbox" for testing
    api_key=AT_API_KEY
)

sms = at.SMS

recipients = [TEST_SMS_RECIPIENT]

try:
    response = sms.send(
        message="Hello from Fahamika! This is a test SMS from the sandbox.",
        recipients=recipients,
    )
    print("✅ SMS sent successfully!")
    print(response)
except Exception as e:
    print(f"❌ Failed to send: {e}")