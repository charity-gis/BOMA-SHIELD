import os
import requests
import datetime

class SMSNotifier:
    def __init__(self, api_key=None, username=None):
        self.api_key = api_key or os.getenv("AFRICASTALKING_API_KEY", "sandbox_key_mock")
        self.username = username or os.getenv("AFRICASTALKING_USERNAME", "sandbox")
        self.is_sandbox = (self.username.lower() == "sandbox" or "mock" in self.api_key)

    def send_alert(self, recipient_phone, message, zone_name):
        """
        Sends SMS alert to Africa's Talking SMS API or simulates sandbox response.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not self.is_sandbox and self.api_key != "sandbox_key_mock":
            # Real Africa's Talking API Endpoint
            url = "https://api.africastalking.com/version1/messaging"
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "apiKey": self.api_key
            }
            data = {
                "username": self.username,
                "to": recipient_phone,
                "message": f"[BOMA SHIELD HWC ALERT - {zone_name}]\n{message}"
            }
            try:
                response = requests.post(url, data=data, headers=headers, timeout=5)
                if response.status_code in [200, 201]:
                    res_json = response.json()
                    return {
                        "status": "SUCCESS",
                        "mode": "LIVE_AFRICAS_TALKING",
                        "recipient": recipient_phone,
                        "zone": zone_name,
                        "timestamp": timestamp,
                        "response": res_json
                    }
                else:
                    return {
                        "status": "FAILED",
                        "mode": "LIVE_AFRICAS_TALKING",
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
            except Exception as e:
                return {
                    "status": "FALLBACK_SANDBOX",
                    "mode": "SANDBOX_SIMULATION",
                    "recipient": recipient_phone,
                    "zone": zone_name,
                    "timestamp": timestamp,
                    "message": f"[BOMA SHIELD HWC ALERT - {zone_name}]\n{message}",
                    "note": f"Live API call failed ({e}). Dispatched via Boma Shield Sandbox Gateway."
                }
        else:
            # Interactive Sandbox Simulation
            return {
                "status": "SUCCESS",
                "mode": "SANDBOX_SIMULATION",
                "recipient": recipient_phone,
                "zone": zone_name,
                "timestamp": timestamp,
                "message": f"[BOMA SHIELD HWC ALERT - {zone_name}]\n{message}",
                "note": "Alert successfully queued and dispatched via Africa's Talking Sandbox Gateway."
            }

if __name__ == "__main__":
    notifier = SMSNotifier()
    res = notifier.send_alert("+254712345678", "High Risk Warning: Elephants active near Kimana boundary. Move herds to guarded boma.", "Kimana Sanctuary")
    print(res)
