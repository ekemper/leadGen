import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
load_dotenv()
print("sys.path:", sys.path)

from server.background_services.email_verifier_service import EmailVerifierService

def test_email_verifier_api():
    # Dummy email for testing
    email = "dummy.email@example.com"
    service = EmailVerifierService()
    response = service.verify_email(email)
    print("Email Verifier API response:", response)

if __name__ == "__main__":
    api_key = os.getenv("MILLIONVERIFIER_API_KEY")
    if not api_key:
        print("Error: MILLIONVERIFIER_API_KEY environment variable is not set.")
        sys.exit(1)
    test_email_verifier_api() 