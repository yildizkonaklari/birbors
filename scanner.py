import yfinance as yf
import requests
import os
import pandas as pd
import time
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# --- ANTIBLOCK FIX ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
})

# SSL Hatası Fix
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
session.verify = False

# Monkey Patch yfinance
import yfinance.shared as shared
if hasattr(shared, '_create_session'):
    shared._create_session = lambda: session
    
_original_get = requests.get
def patched_get(*args, **kwargs):
    kwargs.setdefault('headers', session.headers)
    kwargs.setdefault('verify', False)
    return _original_get(*args, **kwargs)
requests.get = patched_get

# --- AYARLAR ---
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
warnings.filterwarnings("ignore")

SEMBOLLER = [
    "AEFES.IS", "AGHOL.IS", "AKBNK.IS", "AKSEN.IS", "ALARK.IS",
    "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "BIMAS.IS", "BRSAN.IS",
    "CANTE.IS", "CIMSA.IS", "DOAS.IS", "DOHOL.IS", "ECILC.IS",
    "EKGYO.IS", "ENJSA.IS", "ENKAI.IS", "EREGL.IS", "EUPWR.IS",
    "FROTO.IS", "GARAN.IS", "GESAN.IS", "GUBRF.IS", "HALKB.IS",
    "HEKTS.IS", "ISCTR.IS", "ISGYO.IS", "KCHOL.IS", "KONTR.IS",
    "KOZAA.IS", "KOZAL.IS", "KRDMD.IS", "MGROS.IS", "ODAS.IS",
    "OYAKC.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS",
    "SISE.IS", "SMRTG.IS", "SOKM.IS", "TAVHL.IS", "TCELL.IS",
    "THYAO.IS", "TOASO.IS", "TSKB.IS", "TTKOM.IS", "TUPRS.IS",
    "VAKBN.IS", "VESTL.IS", "YKBNK.IS"
]

# Ortam Değişkenleri
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Supabase Fallback Logic
SUPABASE_URL = os.environ.get("SUPABASE_URL")
if not SUPABASE_URL:
    SUPABASE_URL = "https://ckgwpxsaclakcdzitzrb.supabase.co"

SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_KEY:
    # Default Anon/Public Key fallback
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNrZ3dweHNhY2xha2Nkeml0enJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzNjAzMjQsImV4cCI6MjA4NjkzNjMyNH0.Hl02XgwwHOWyYrI0fcH7OH19IwTSFX4z5Zhjlc8rvQY"

def print_settings_check():
    print(f"--- AYARLAR KONTROL ---")
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Supabase Key: {'TANIZMI (Uzunluk: ' + str(len(SUPABASE_KEY)) + ')' if SUPABASE_KEY else 'EKSIK'}")
    
    # Telegram Debug (Masked)
    if TELEGRAM_TOKEN:
        masked_token = TELEGRAM_TOKEN[:5] + "..." + TELEGRAM_TOKEN[-5:]
        print(f"Telegram Token: TANIMLI ({masked_token})")
    else:
        print(f"Telegram Token: EKSIK (None veya Bos)")
        
    print(f"Chat ID: {CHAT_ID if CHAT_ID else 'EKSIK'}")
    print(f"-----------------------")

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_sma(series, period=50):
    return series.rolling(window=period).mean()

def send_telegram(message):
    if TELEGRAM_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Telegram hatası: {e}")
    else:
        print("Telegram kimlik bilgileri eksik. Mesaj gönderilmedi.")

def save_to_db(data):
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            url = f"{SUPABASE_URL}/rest/v1/signals"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
            kayit = {
                "symbol": data["symbol"],
                "price": data["price"],
                "rsi": data["rsi"],
                "status": "AL"
            }
            response = requests.post(url, json=kayit, headers=headers)
            if response.status_code in [200, 201]:
                print(f"{data['symbol']} veritabanına kaydedildi.")
            else:
                print(f"Supabase Hatası: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Veritabanı hatası: {e}")
    else:
        print(f"Supabase kimlik bilgileri eksik. {data['symbol']} kaydedilmedi.")

def analiz_et(symbol):
    try:
        # Veri Çekme
        df_w = yf.download(symbol, period="2y", interval="1wk", progress=False, auto_adjust=True)
        df_h = yf.download(symbol, period="1mo", interval="1h", progress=False, auto_adjust=True)

        if len(df_w) < 50 or len(df_h) < 14: return None

        # MultiIndex fix
        if isinstance(df_w.columns, pd.MultiIndex):
             try:
                df_w = df_w.xs(symbol, level=1, axis=1)
                df_h = df_h.xs(symbol, level=1, axis=1)
             except: pass 

        # SMA 50
        df_w['SMA_50'] = calculate_sma(df_w['Close'], 50)
        if pd.isna(df_w['SMA_50'].iloc[-1]): return None
            
        trend_up = df_w['Close'].iloc[-1] > df_w['SMA_50'].iloc[-1]

        # Support
        last_year = df_w.tail(52)
        high_p = last_year['High'].max()
        low_p = last_year['Low'].min()
        fib_0618 = high_p - ((high_p - low_p) * 0.618)
        on_support = abs(df_w['Close'].iloc[-1] - fib_0618) <= (df_w['Close'].iloc[-1] * 0.03)

        # RSI
        df_h['RSI'] = calculate_rsi(df_h['Close'], 14)
        if len(df_h['RSI']) < 1: return None
        rsi_val = df_h['RSI'].iloc[-1]
        if pd.isna(rsi_val): return None
        
        oversold = rsi_val < 35

        # Formasyon
        open_p = df_h['Open'].iloc[-1]
        close_p = df_h['Close'].iloc[-1]
        high_h = df_h['High'].iloc[-1]
        low_h = df_h['Low'].iloc[-1]
        
        body = abs(close_p - open_p)
        full = high_h - low_h
        if full == 0: return None
        lower_shadow = min(open_p, close_p) - low_h
        is_reversal = (body <= full * 0.15) or (lower_shadow >= body * 2)

        # KARAR (Canlı Mod: RSI < 35)
        # Strateji: RSI < 35 olduğunda 'AL' sinyali ver.
        # İsteğe bağlı olarak 'trend_up' ve 'on_support' eklenebilir.
        if oversold: 
            # Hedefler
            stop_loss = low_h * 0.95
            tp1 = close_p * 1.05
            tp2 = close_p * 1.10
            
            risk = close_p - stop_loss
            reward = tp1 - close_p

            return {
                "symbol": symbol,
                "price": round(close_p, 2),
                "rsi": round(rsi_val, 2),
                "stop_loss": round(stop_loss, 2),
                "target_1": round(tp1, 2),
                "target_2": round(tp2, 2),
                "note": "RSI < 35 (Aşırı Satım) Sinyali"
            }
            
    except Exception as e:
        return None

def main():
    print_settings_check() # Debug için ayarları yazdır
    print("Tarama başlatılıyor...")
    sinyaller = []

    for sembol in SEMBOLLER:
        print(f"Analiz ediliyor: {sembol}", flush=True)
        sonuc = analiz_et(sembol)
        if sonuc:
            print(f"\nSinyal bulundu: {sembol}")
            sinyaller.append(sonuc)
            save_to_db(sonuc)
        time.sleep(1) 

    print(f"\nTarama bitti. Toplam {len(sinyaller)} sinyal bulundu.")
    
    if sinyaller:
        print("Telegram mesajı hazırlanıyor...")
        mesajlar = []
        current_msg = "🚨 **CANLI ALIM FIRSATI (RSI < 35)** 🚨\n\n"
        
        for s in sinyaller:
            item_str = f"💎 *{s['symbol']}*\n"
            item_str += f"💵 {s['price']} | RSI: {s['rsi']}\n"
            item_str += f"🎯 TP1: {s['target_1']} | 🛑 STOP: {s['stop_loss']}\n"
            item_str += "----------------------\n"
            
            if len(current_msg) + len(item_str) > 3500:
                mesajlar.append(current_msg)
                current_msg = "🚨 **DEVAMI** 🚨\n\n" + item_str
            else:
                current_msg += item_str
                
        mesajlar.append(current_msg)
        
        for msg in mesajlar:
            try:
                send_telegram(msg)
                print("Telegram mesaj parçası gönderildi.")
                time.sleep(1) 
            except Exception as e:
                print(f"Telegram gönderme hatası: {e}")
    else:
        print("Sinyal yok. (Filtreler gevşetildiği halde bulunamadıysa veri çekme sorunu olabilir)")

if __name__ == "__main__":
    main()
