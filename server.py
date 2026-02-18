import http.server
import socketserver
import json
import yfinance as yf
from urllib.parse import urlparse, parse_qs

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
        else:
            # Standart dosya sunumu (index.html vb.)
            super().do_GET()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"Sunucu çalışıyor: http://localhost:{PORT}")
        print("Durdurmak için Ctrl+C basın.")
        httpd.serve_forever()
