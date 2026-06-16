"""Test Meta Conversions API (server-side events)."""
import os, sys, httpx, json, hashlib, time
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
TOKEN    = os.environ["META_ACCESS_TOKEN"]
PIXEL_ID = os.environ["META_PIXEL_ID"]
GRAPH    = "https://graph.facebook.com/v20.0"

def sha256(val):
    return hashlib.sha256(val.strip().lower().encode()).hexdigest()

# Send a test PageView event via CAPI
test_event = {
    "data": [
        {
            "event_name": "PageView",
            "event_time": int(time.time()),
            "action_source": "website",
            "event_source_url": "https://thematchatee.com/",
            "user_data": {
                "client_ip_address": "1.2.3.4",
                "client_user_agent": "Mozilla/5.0 (test)",
            },
        }
    ],
    "test_event_code": "TEST12345",  # This sends to Test Events tab in Events Manager
    "access_token": TOKEN,
}

r = httpx.post(
    f"{GRAPH}/{PIXEL_ID}/events",
    json=test_event,
    timeout=20,
)
print(f"CAPI test event: {r.status_code}")
if r.status_code == 200:
    print(f"  Response: {r.json()}")
    print(f"\n  SUCCESS! Conversions API is working.")
    print(f"  Check Test Events in Meta Events Manager to confirm receipt.")
else:
    print(f"  Error: {r.text[:400]}")
    print(f"\n  Token may need 'ads_management' or specific CAPI permissions.")
    print(f"  To get a dedicated CAPI token:")
    print(f"  Meta Business Suite -> Events Manager -> Pixels -> {PIXEL_ID}")
    print(f"  -> Settings -> Conversions API -> Generate access token")
