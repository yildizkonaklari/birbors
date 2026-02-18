import http.server
import socketserver
import json
import yfinance as yf
from urllib.parse import urlparse, parse_qs
import requests
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# --- ANTIBLOCK FIX ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
})
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
session.verify = False

import yfinance.shared as shared
if hasattr(shared, '_create_session'):
    shared._create_session = lambda: session
    
_original_get = requests.get
def patched_get(*args, **kwargs):
    kwargs.setdefault('headers', session.headers)
    return _original_get(*args, **kwargs)
requests.get = patched_get

import os

import os

import os

PORT = int(os.environ.get("PORT", 8000))

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        # API Endpoint: /api/quote/<SYMBOL>
        if parsed_path.path.startswith("/api/quote/"):
            try:
                # Sembolü url'den al
                symbol = parsed_path.path.split("/")[-1]
                
                # yfinance ile veri çek
                ticker = yf.Ticker(symbol)
                # fast_info genelde daha hızlıdır
                price = ticker.fast_info.last_price
                prev_close = ticker.fast_info.previous_close
                
                if price is None:
                    # Alternatif (history)
                    df = ticker.history(period="2d")
                    if not df.empty:
                        price = df['Close'].iloc[-1]
                        prev_close = df['Close'].iloc[-2] if len(df) > 1 else price
                
                if price:
                    data = {
                        "symbol": symbol,
                        "price": price,
                        "prev_close": prev_close
                    }
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*') # Gerekirse
                    self.end_headers()
                    self.wfile.write(json.dumps(data).encode('utf-8'))
                else:
                    self.send_error(404, "Data not found")
                    
            except Exception as e:
                self.send_error(500, str(e))

        elif parsed_path.path.startswith("/api/analyze/"):
            try:
                # Sembolü url'den al
                symbol = parsed_path.path.split("/")[-1]
                
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key or not OpenAI:
                    self.send_error(500, "OpenAI API Key eksik veya kütüphane yüklü değil.")
                    return

                # Basit veri çekimi
                ticker = yf.Ticker(symbol)
                info = ticker.fast_info
                
                # Prompt hazırlığı
                prompt = f"""
                Sen uzman bir borsa analistisin. Aşağıdaki verileri kullanarak {symbol} hissesi için 
                kısa, etkileyici ve yatırımcıya yön gösteren Türkçe bir analiz yaz. 
                Yatırım tavsiyesi olmadığını belirten standart bir uyarı ekle ama metni boğma.
                
                Veriler:
                - Fiyat: {info.last_price}
                - Önceki Kapanış: {info.previous_close}
                - Piyasa Değeri: {info.market_cap}
                - 52 Hafta En Yüksek: {info.year_high}
                - 52 Hafta En Düşük: {info.year_low}
                
                Analiz (Max 3 cümle):
                """
                
                client = OpenAI(api_key=api_key)
                completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Sen yardımcı bir finans asistanısın."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                analysis_text = completion.choices[0].message.content
                
                response_data = {"symbol": symbol, "analysis": analysis_text}
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
                
            except Exception as e:
                 self.send_error(500, f"AI Hatası: {str(e)}")

        else:
            # Standart dosya sunumu (index.html vb.)
            super().do_GET()

if __name__ == "__main__":
    import threading
    import time
    import scanner

    def run_scanner_loop():
        """Arka planda periyodik olarak tarama yapar"""
        # İlk çalışmada biraz bekle ki sunucu ayağa kalksın
        time.sleep(10) 
        while True:
            try:
                print("\n[Scheduler] Otomatik tarama başlatılıyor...", flush=True)
                scanner.main()
                print("[Scheduler] Tarama tamamlandı. 15 dakika bekleniyor...", flush=True)
            except Exception as e:
                print(f"[Scheduler] Hata: {e}", flush=True)
            
            # 15 Dakika bekle (900 saniye)
            time.sleep(900)

    # Scanner thread'ini başlat (Daemon = True, ana program kapanınca bu da kapanır)
    t = threading.Thread(target=run_scanner_loop, daemon=True)
    t.start()

    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"Sunucu çalışıyor: http://localhost:{PORT}")
        print("Otomatik tarama modülü aktif (15 dk arayla).")
        print("Durdurmak için Ctrl+C basın.")
        httpd.serve_forever()
