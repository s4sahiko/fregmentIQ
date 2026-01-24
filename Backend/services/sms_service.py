import os
from typing import Dict, Optional
import time
from config import SMS_CONFIG

class SmsService:
    def __init__(self):
        self.config = SMS_CONFIG
        self.last_status: Dict[int, str] = {}
        self.last_alert_time: Dict[int, float] = {}
        self.cooldown_period = 300  # 5 minutes cooldown between duplicate alerts if needed
        
        # Initialize Twilio client if enabled
        self.client = None
        if self.config["provider"] == "twilio" and self.config["twilio_sid"]:
            try:
                from twilio.rest import Client
                self.client = Client(
                    self.config["twilio_sid"], 
                    self.config["twilio_auth_token"]
                )
            except ImportError:
                print("[SmsService] Twilio library not found. Run 'pip install twilio' to use Twilio provider.")
            except Exception as e:
                print(f"[SmsService] Error initializing Twilio client: {e}")

    def check_alert_condition(self, batch_number: int, current_status: str) -> Optional[str]:
        """
        Check if an alert is needed. Returns the PREVIOUS status if alert needed, else None.
        Updates internal state.
        """
        # If this is the first time we see this batch
        if batch_number not in self.last_status:
            self.last_status[batch_number] = current_status
            
            # Alert on startup if status is ALREADY bad (warning or critical)
            if current_status in ["warning", "critical", "failed", "concerning"]:
                return "unknown" # Previous status was unknown
            
            return None
            
        previous_status = self.last_status[batch_number]
        
        # Alert if status has changed
        if current_status != previous_status:
            # Update known status
            self.last_status[batch_number] = current_status
            return previous_status
            
        return None

    def send_alert(self, batch_number: int, current_status: str, previous_status: str, details: str = ""):
        """
        Send an SMS alert
        """
        if not self.config["enabled"]:
            return

        # Construct message
        emoji_map = {
            "perfect": "✅",
            "acceptable": "👌",
            "concerning": "⚠️",
            "failed": "❌",
            "critical": "🚨"
        }
        
        status_emoji = emoji_map.get(current_status, "ℹ️")
        
        message_body = (
            f"FermentIQ Alert: Batch #{batch_number} status changed.\n"
            f"Old: {previous_status}\n"
            f"New: {current_status.upper()} {status_emoji}\n"
            f"Details: {details}"
        )
        
        target_number = self.config["target_numbers"].get(str(batch_number)) or self.config["target_numbers"].get("default")
        
        if self.config["provider"] == "twilio" and self.client:
            try:
                message = self.client.messages.create(
                    body=message_body,
                    from_=self.config["twilio_from_number"],
                    to=target_number
                )
                print(f"[SmsService] SMS sent to {target_number}: SID {message.sid}")
            except Exception as e:
                print(f"[SmsService] Failed to send SMS via Twilio: {e}")
        else:
            # Console provider (simulation)
            print("="*40)
            print(f"📱 [SMS SIMULATION] To: {target_number}")
            print(f"Content: {message_body}")
            print("="*40)

# Singleton instance
_sms_service = None

def get_sms_service():
    global _sms_service
    if _sms_service is None:
        _sms_service = SmsService()
    return _sms_service
