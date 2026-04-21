import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY")

async def send_otp_email(email: str, otp: str):
    """
    Sends an OTP code via email. 
    Currently supports Resend API if RESEND_API_KEY is provided, 
    otherwise falls back to logging to terminal.
    """
    
    # Logic for Resend
    if RESEND_API_KEY:
        try:
            import resend
            resend.api_key = RESEND_API_KEY
            
            params = {
                "from": "NUS Course Agent <onboarding@resend.dev>",
                "to": [email],
                "subject": "Your Verification Code - NUS Course Agent",
                "html": f"""
                <div style="font-family: sans-serif; padding: 20px; color: #333;">
                    <h2 style="color: #4f46e5;">Verification Code</h2>
                    <p>Your 6-digit code for <strong>NUS Course Agent</strong> is:</p>
                    <div style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #4f46e5; margin: 20px 0;">
                        {otp}
                    </div>
                    <p style="font-size: 12px; color: #666;">This code will expire in 10 minutes.</p>
                </div>
                """
            }
            resend.Emails.send(params)
            logger.info(f"OTP sent via Resend to {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email via Resend: {e}")
            # Fallback to terminal anyway
    
    # Fallback / Local Debug
    print("\n" + "="*50)
    print(f" [LOCAL DEBUG] OTP for {email}: {otp}")
    print("="*50 + "\n")
    return True
