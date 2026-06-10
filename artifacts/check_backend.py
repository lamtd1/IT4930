import requests
import sys

try:
    print("Sending request to health endpoint...")
    r = requests.get("http://127.0.0.1:8000/health", timeout=5)
    print("Status code:", r.status_code)
    print("Response:", r.json())
except Exception as e:
    print("Error:", e, file=sys.stderr)
