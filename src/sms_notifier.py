import os
import requests
import datetime

class SMSNotifier:
    def __init__(self, api_key=None, sender_id=None):
        # Default to environment variables or use mock values for the sandbox
        self.api_key = api_key or os.getenv("TALKSASA_API_KEY", "sandbox_key_mock")
        self.sender_id = sender_id or os.getenv("TALKSASA_SENDER_ID", "Talksasa")
        self.is_sandbox = ("mock" in self.api_key)

    def send_alert(self, recipient_phone, message, zone_name):
        """
        Sends SMS alert via the TalkSasa SMS API.
        Requires an API Token generated from the TalkSasa developer portal.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[BOMA SHIELD HWC ALERT - {zone_name}]\n{message}"
        
        if not self.is_sandbox:
            url = "https://bulksms.talksasa.com/api/v3/sms/send"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            # The exact payload required by standard TalkSasa v3 API
            payload = {
                "recipient": recipient_phone,
                "sender_id": self.sender_id,
                "type": "plain",
                "message": full_message
            }
            
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                res_json = response.json()
                
                # Check response. Usually TalkSasa returns 200 with status: 'success' or 'error'
                if response.status_code == 200 and res_json.get("status") == "success":
                    return {
                        "status": "SUCCESS",
                        "mode": "LIVE_TALKSASA",
                        "recipient": recipient_phone,
                        "zone": zone_name,
                        "timestamp": timestamp,
                        "response": res_json
                    }
                else:
                    return {
                        "status": "FAILED",
                        "mode": "LIVE_TALKSASA",
                        "error": f"TalkSasa API Error: {res_json.get('message', response.text)}"
                    }
            except Exception as e:
                return {
                    "status": "FALLBACK_SANDBOX",
                    "mode": "SANDBOX_SIMULATION",
                    "recipient": recipient_phone,
                    "zone": zone_name,
                    "timestamp": timestamp,
                    "message": full_message,
                    "note": f"Live API call failed ({str(e)}). Dispatched via Sandbox."
                }
        else:
            # Interactive Sandbox Simulation
            return {
                "status": "SUCCESS",
                "mode": "SANDBOX_SIMULATION",
                "recipient": recipient_phone,
                "zone": zone_name,
                "timestamp": timestamp,
                "message": full_message,
                "note": "No valid TALKSASA_API_KEY found in .env. Dispatched via Sandbox Simulator."
            }

if __name__ == "__main__":
    notifier = SMSNotifier()
    res = notifier.send_alert("+254712345678", "Hatari kubwa ya mzozo. Endelea kwa tahadhari.", "Kimana Sanctuary")
    print(res)
