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

def calculate_macd(series, fast=12, slow=26, signal=9):
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def analiz_et(symbol):
    try:
        # Veri Çekme
        df_w = yf.download(symbol, period="2y", interval="1wk", progress=False, auto_adjust=True)
        df_h = yf.download(symbol, period="3mo", interval="1d", progress=False, auto_adjust=True) # Günlük Veriye Geçtik (Daha kararlı)

        if len(df_w) < 50 or len(df_h) < 35: return None

        # MultiIndex fix
        if isinstance(df_w.columns, pd.MultiIndex):
             try:
                df_w = df_w.xs(symbol, level=1, axis=1)
                df_h = df_h.xs(symbol, level=1, axis=1)
             except: pass 

        # --- HAFTALIK TREND ANALİZİ ---
        df_w['SMA_50'] = calculate_sma(df_w['Close'], 50)
        if pd.isna(df_w['SMA_50'].iloc[-1]): return None
        
        # Ana Trend Yukarı mı? (Fiyat > Haftalık SMA 50)
        trend_up = df_w['Close'].iloc[-1] > df_w['SMA_50'].iloc[-1]

        # --- GÜNLÜK MOMENTUM & HACİM ---
        # RSI
        df_h['RSI'] = calculate_rsi(df_h['Close'], 14)
        rsi_val = df_h['RSI'].iloc[-1]
        
        # MACD
        macd, signal_line = calculate_macd(df_h['Close'])
        macd_val = macd.iloc[-1]
        signal_val = signal_line.iloc[-1]
        prev_macd = macd.iloc[-2]
        prev_signal = signal_line.iloc[-2]

        # MACD Kesişimi (Alım yönünde mi?)
        # 1. MACD > Sinyal (Mevcut Durum)
        # 2. Yeni Kesişim (Dün altındaydı, bugün üstünde)
        macd_buy = macd_val > signal_val
        macd_cross = (prev_macd < prev_signal) and (macd_val > signal_val)

        # Hacim Artışı
        vol_avg = df_h['Volume'].rolling(window=20).mean().iloc[-1]
        vol_curr = df_h['Volume'].iloc[-1]
        volume_spike = vol_curr > (vol_avg * 1.5) # Ortalamanın %50 fazlası hacim

        # Mum Formasyonu (Dönüş) - Basit
        open_p = df_h['Open'].iloc[-1]
        close_p = df_h['Close'].iloc[-1]
        low_h = df_h['Low'].iloc[-1]
        body = abs(close_p - open_p)
        lower_shadow = min(open_p, close_p) - low_h
        hammer = (lower_shadow > body * 2) # Çekiç Formasyonu

        # --- KARAR MEKANİZMASI (KOMBO) ---
        # Senaryo 1: Güçlü Trend Dönüşü (Trend Yukarı + RSI Uygun + MACD Kesişimi)
        strong_reversal = trend_up and (rsi_val < 50) and macd_cross

        # Senaryo 2: Aşırı Satım Tepkisi (RSI < 30 + Hacim Patlaması veya Çekiç)
        oversold_bounce = (rsi_val < 35) and (volume_spike or hammer)

        if strong_reversal or oversold_bounce:
            signal_type = "GÜÇLÜ DÖNÜŞ" if strong_reversal else "TEPKİ ALIMI"
            
            stop_loss = low_h * 0.97
            tp1 = close_p * 1.05
            
            return {
                "symbol": symbol,
                "price": round(close_p, 2),
                "rsi": round(rsi_val, 2),
                "stop_loss": round(stop_loss, 2),
                "target_1": round(tp1, 2),
                "target_2": round(close_p * 1.10, 2),
                "note": f"{signal_type} | MACD: {'AL' if macd_buy else 'SAT'} | Vol: {'YÜKSEK' if volume_spike else 'NORMAL'}"
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
