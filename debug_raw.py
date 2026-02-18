import requests
import warnings

warnings.filterwarnings("ignore")

URL = "https://query1.finance.yahoo.com/v8/finance/chart/THYAO.IS?interval=1d&range=1mo"

print(f"Requesting: {URL}")

try:
    # 1. Standart Request
    print("\n--- 1. Standart Request ---")
    r = requests.get(URL, timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Content-Type: {r.headers.get('Content-Type')}")
    print(f"Body (First 100 ch): {r.text[:100]}")
except Exception as e:
    print(f"Hata: {e}")

try:
    # 2. SSL Bypass + Headers
    print("\n--- 2. SSL Bypass + Headers ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    r = requests.get(URL, headers=headers, verify=False, timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Content-Type: {r.headers.get('Content-Type')}")
    print(f"Body (First 100 ch): {r.text[:100]}")
except Exception as e:
    print(f"Hata: {e}")
