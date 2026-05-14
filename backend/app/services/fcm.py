import firebase_admin
from firebase_admin import credentials, messaging
from typing import List, Dict, Any
import os
from app.core.config import settings

class FCMService:
    def __init__(self):
        self.initialized = False
        self.cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "/app/serviceAccountKey.json")
        
        if os.path.exists(self.cred_path):
            try:
                cred = credentials.Certificate(self.cred_path)
                firebase_admin.initialize_app(cred)
                self.initialized = True
                print(f"Firebase Admin initialized with credentials from {self.cred_path}")
            except Exception as e:
                print(f"Failed to initialize Firebase Admin: {e}")
        else:
            print(f"Firebase credentials not found at {self.cred_path}. Push notifications will be disabled.")

    def send_push(self, tokens: List[str], title: str, body: str, data: Dict[str, str] = None):
        """Send push notification to a list of registration tokens."""
        if not self.initialized or not tokens:
            return

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data,
            tokens=tokens,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default',
                    tag=data.get("type") if data else None, # Group notifications by type
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1, # This is for the app icon badge
                    ),
                ),
            ),
        )
        
        try:
            response = messaging.send_multicast(message)
            print(f"Successfully sent {response.success_count} messages")
            if response.failure_count > 0:
                print(f"Failed to send {response.failure_count} messages")
            return response
        except Exception as e:
            print(f"Error sending FCM message: {e}")
            return None

fcm_service = FCMService()
