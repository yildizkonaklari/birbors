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

                # Veri Çekimi (Genişletilmiş)
                ticker = yf.Ticker(symbol)
                info = ticker.fast_info
                
                # Tarihsel Veri (Trend ve Hacim Analizi için son 1 ay)
                hist = ticker.history(period="1mo")
                hist_str = hist.tail(10).to_string() # Son 10 günü text olarak ver

                # Prompt Hazırlığı (Gelişmiş)
                system_prompt = """
                Sen kıdemli bir "Equity Research + Quant" analistisin. 
                Amacın, veri-temelli, çelişkileri yakalayan, riskleri açıkça yazan ve senaryolar üreten kapsamlı bir analiz raporu üretmek.
                Yatırım tavsiyesi vermeden (YTD), tamamen objektif ve stratejik bir dille yaz.
                """
                
                user_prompt = f"""
                Analiz Edilecek Hisse: {symbol}
                
                CANLI VERİLER:
                - Fiyat: {info.last_price}
                - Önceki Kapanış: {info.previous_close}
                - Piyasa Değeri: {info.market_cap}
                - 52 Hafta: {info.year_low} - {info.year_high}
                
                SON 10 GÜNLÜK İŞLEM VERİLERİ (Trend ve Hacim Teyidi İçin):
                {hist_str}
                
                Lütfen aşağıdaki yapıda detaylı bir analiz yap:
                
                1. **ÖZET KARAR & VADE ANALİZİ**
                   - Alım/Satım/Bekle/Kademeli Topla kararını gerekçesiyle belirt.
                   - Kısa, Orta ve Uzun Vade beklentilerini ayır.
                
                2. **VALÜASYON & ÇARPANLAR**
                   - Mevcut fiyatı emsallerine veya geçmişine göre ucuz mu yoksa "haklı bir indirim" mi? (Yorumla)
                
                3. **TEKNİK ANALİZ & MOMENTUM**
                   - Trend (1 Günlük/1 Haftalık) durumu.
                   - Ana Destek ve Direnç seviyeleri.
                   - Hacim analizi (Kırılım tuzağı riski var mı?).
                   - RSI/MACD gibi momentum indikatörleri üzerinden yorum (Aşırı alım/satım?).
                
                4. **SENARYOLAR**
                   - **İyi Senaryo:** Hangi seviye geçilirse yükseliş hızlanır?
                   - **Kötü Senaryo:** Hangi destek kırılırsa stop olunmalı?
                
                5. **RİSK & ÇELİŞKİLER**
                   - Temel veya teknikte gördüğün en büyük risk nedir?
                
                Not: Cevabı Markdown formatında, okunaklı başlıklarla ver.
                """
                
                client = OpenAI(api_key=api_key)
                completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7
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
