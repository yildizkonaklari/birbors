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


import os

PORT = int(os.environ.get("PORT", 8000))

# --- SUPABASE CONFIG ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ckgwpxsaclakcdzitzrb.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNrZ3dweHNhY2xha2Nkeml0enJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzNjAzMjQsImV4cCI6MjA4NjkzNjMyNH0.Hl02XgwwHOWyYrI0fcH7OH19IwTSFX4z5Zhjlc8rvQY")

# --- AUTO PILOT INIT ---
from autopilot import AutoPilot
autopilot_system = AutoPilot()

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/api/autopilot/toggle":
            try:
                length = int(self.headers.get('content-length', 0))
                body = self.rfile.read(length).decode('utf-8')
                data = json.loads(body) # Expect {"state": true/false}
                
                new_state = autopilot_system.toggle(data.get("state", False))
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"active": new_state}).encode('utf-8'))
            except Exception as e:
                 self.send_error(500, str(e))

        elif parsed_path.path == "/api/autopilot/reset":
            autopilot_system.reset()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"RESET OK")

    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        # --- AUTO PILOT API ---
        if parsed_path.path == "/api/autopilot/status":
             status = autopilot_system.get_status()
             self.send_response(200)
             self.send_header('Content-type', 'application/json')
             self.send_header('Access-Control-Allow-Origin', '*')
             self.end_headers()
             self.wfile.write(json.dumps(status, ensure_ascii=False).encode('utf-8'))

        # API Endpoint: /api/quote/<SYMBOL>
        elif parsed_path.path.startswith("/api/quote/"):
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

        elif parsed_path.path == "/api/portfolio/summary":
            try:
                # 1. İşlemleri Çek (Supabase 'transactions' tablosu)
                if not SUPABASE_URL or not SUPABASE_KEY:
                    raise Exception("Supabase ayarları eksik")
                
                url = f"{SUPABASE_URL}/rest/v1/transactions?select=*"
                headers = {
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                }
                
                resp = requests.get(url, headers=headers)
                if resp.status_code != 200:
                    transactions = [] # Tablo yoksa veya boşsa
                else:
                    transactions = resp.json()

                # 2. Portföy Durumunu Hesapla
                holdings = {} # {symbol: {quantity: 0, avg_cost: 0, total_cost: 0}}
                
                for t in transactions:
                    sym = t['symbol']
                    qty = int(t['amount'])
                    price = float(t['price'])
                    typ = t['type'] # 'BUY' or 'SELL'
                    
                    if sym not in holdings:
                        holdings[sym] = {'quantity': 0, 'total_cost': 0}
                    
                    if typ == 'BUY':
                        holdings[sym]['quantity'] += qty
                        holdings[sym]['total_cost'] += (qty * price)
                    elif typ == 'SELL':
                        # Basit mantık: Ortalama maliyet değişmez, miktar azalır
                        # (FIFO/LIFO karmaşasına girmeden basit ağırlıklı ortalama)
                        if holdings[sym]['quantity'] > 0:
                            avg_cost = holdings[sym]['total_cost'] / holdings[sym]['quantity']
                            holdings[sym]['total_cost'] -= (qty * avg_cost)
                            holdings[sym]['quantity'] -= qty

                # 3. Güncel Fiyatları Al ve P/L Hesapla
                portfolio_summary = {
                    "total_value": 0.0,
                    "total_cost": 0.0,
                    "total_pl": 0.0,
                    "items": []
                }
                
                for sym, data in holdings.items():
                    if data['quantity'] > 0:
                        # Güncel fiyatı al (Hata yönetimi ile)
                        current_price = 0
                        try:
                            ticker = yf.Ticker(sym)
                            # fast_info bazen hata verebilir, safe access
                            current_price = ticker.fast_info.last_price
                        except Exception as ye:
                            print(f"{sym} fiyat hatası: {ye}")
                            # Fallback: fiyat 0 ise hesaplamaya katılmaz veya eski fiyat bulunur
                        
                        if current_price is None: current_price = 0
                        
                        market_value = data['quantity'] * current_price
                        avg_cost = data['total_cost'] / data['quantity']
                        pl = market_value - data['total_cost']
                        pl_percent = (pl / data['total_cost']) * 100 if data['total_cost'] > 0 else 0
                        
                        portfolio_summary['total_value'] += market_value
                        portfolio_summary['total_cost'] += data['total_cost']
                        portfolio_summary['total_pl'] += pl
                        
                        portfolio_summary['items'].append({
                            "symbol": sym,
                            "quantity": data['quantity'],
                            "avg_cost": round(avg_cost, 2),
                            "current_price": round(current_price, 2),
                            "market_value": round(market_value, 2),
                            "pl": round(pl, 2),
                            "pl_percent": round(pl_percent, 2)
                        })

                # API Yanıtı
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(portfolio_summary, ensure_ascii=False).encode('utf-8'))

            except Exception as e:
                self.send_error(500, f"Portföy Hatası: {str(e)}")

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
                
                # Sinyalleri scanner'dan al
                # Scanner.main() yerine, scanner logic'ini alıp sonuç döndürmeli
                # Scanner modulunde minor degisiklik gerekebilir ama simdilik
                # scanner.py'nin kendi icindeki save_to_db fonksiyonuna mudahale etmeden
                # Sinyal listesini döndüren bir versiyon yazmadık.
                # PRATİK ÇÖZÜM: Scanner'ı modifiye etmeden, scanner.py 'main'i sinyalleri
                # bir global listeye atacak şekilde de kullanabiliriz ama en temizi wrapper.
                
                # --- AUTO PILOT INTEGRASYONU ---
                # Scanner çalışır, veritabanına yazar.
                # Biz ayrıca autopilot için özel bir tarama çalıştıralım (aynı logic)
                # VEYA scanner.py'ye sonuc döndürme yeteneği ekleyelim.
                # Şimdilik scanner.py'yi import edip iç fonksiyonu kullanalım:
                
                found_signals = []
                for sembol in scanner.SEMBOLLER:
                     res = scanner.analiz_et(sembol)
                     if res: found_signals.append(res)
                     time.sleep(0.5) # Server yükünü azalt
                
                if found_signals:
                    print(f"[AutoPilot] {len(found_signals)} sinyal bulundu, işleniyor...")
                    autopilot_system.process_signals(found_signals)
                else:
                    # Ayrıca Stop-Loss kontrolü yap (Sinyal olmasa bile fiyat kontrolü lazım)
                    # Bunun için hisselerin güncel fiyatlarını çekmek lazım
                    # AutoPilot içinde check_stops fonksiyonu var ama fiyatları dışardan bekliyor.
                    # Basitlik adına: Sadece tarama döngüsünde stop kontrolü yapalım.
                    pass
                
                # Mevcut portföydeki hisselerin güncel fiyatlarını alıp stop kontrolü yap
                status = autopilot_system.get_status()
                holdings = status.get("holdings", {})
                current_prices = {}
                for sym in holdings.keys():
                    try:
                        ticker = yf.Ticker(sym)
                        p = ticker.fast_info.last_price
                        if p: current_prices[sym] = p
                    except: pass
                
                if current_prices:
                    autopilot_system.check_stops(current_prices)

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
