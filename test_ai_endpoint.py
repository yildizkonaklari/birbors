import requests
import os
import json

# Bu testi çalıştırmadan önce server.py'nin çalıştığından emin olun.
# Ayrıca OPENAI_API_KEY çevresel değişkeninin ayarlı olması gerekir.

BASE_URL = "http://localhost:8000"
SYMBOL = "THYAO.IS"

def test_analyze():
    print(f"Testing analysis for {SYMBOL}...")
    try:
        response = requests.get(f"{BASE_URL}/api/analyze/{SYMBOL}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n--- SUCCESS ---")
            print(f"Symbol: {data.get('symbol')}")
            print(f"Analysis: {data.get('analysis')}")
            return True
        else:
            print("\n--- FAILED ---")
            print(f"Status Code: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n--- EXCEPTION ---")
        print(str(e))
        return False

if __name__ == "__main__":
    # Basit bir kontrol: Sunucu ayakta mı?
    try:
        requests.get(BASE_URL)
        test_analyze()
    except requests.exceptions.ConnectionError:
        print("HATA: Sunucu (server.py) çalışmıyor gibi görünüyor. Lütfen önce sunucuyu başlatın.")
