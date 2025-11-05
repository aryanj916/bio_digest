import resend
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ResendClient:
    """Send emails via Resend API."""
    
    def __init__(self, api_key: str, config: dict):
        resend.api_key = api_key
        self.config = config
        self.from_email = config['digest']['from_email']
        self.from_name = config['digest']['from_name']
    
    def send_digest(self, 
                   recipients: List[str],
                   subject: str,
                   html_content: str) -> bool:
        """Send the digest email to recipients."""
        
        from_address = f"{self.from_name} <{self.from_email}>"
        
        try:
            response = resend.Emails.send({
                "from": from_address,
                "to": recipients,
                "subject": subject,
                "html": html_content
            })
            
            logger.info(f"Email sent successfully to {', '.join(recipients)}")
            logger.info(f"Resend response ID: {response.get('id')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_test(self, recipient: str, html_content: str) -> bool:
        """Send a test email to a single recipient."""
        subject = f"[TEST] Droyd Robotics Digest - {datetime.now().strftime('%Y-%m-%d')}"
        
        return self.send_digest(
            recipients=[recipient],
            subject=subject,
            html_content=html_content
        )