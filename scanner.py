import yfinance as yf
import requests
import os
import pandas as pd
import time
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
warnings.filterwarnings("ignore")
# Original session remains
import yfinance as yf # Keep import

# --- AYARLAR ---

# --- AYARLAR ---
# BIST 50 (BIST 30 Dahil) Hisseleri - Yahoo Finance Formatı
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
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

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
    """Sinyali veritabanına kaydeder (Supabase REST API ile)"""
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            url = f"{SUPABASE_URL}/rest/v1/signals"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
            
            # Veriyi hazırla
            kayit = {
                "symbol": data["symbol"],
                "price": data["price"],
                "rsi": data["rsi"],
                "status": "AL" # Şimdilik sadece AL sinyali üretiyoruz
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
        # --- 1. VERİ ÇEKME ---
        # Haftalık Veri
        df_w = yf.download(symbol, period="2y", interval="1wk", progress=False, auto_adjust=True)
        # Saatlik Veri
        df_h = yf.download(symbol, period="1mo", interval="1h", progress=False, auto_adjust=True)

        if len(df_w) < 50 or len(df_h) < 14: 
            return None

        # --- 2. HAFTALIK ANALİZ ---
        # Sütun isimleri bazen MultiIndex olabilir, düzeltmek gerekebilir
        # yfinance son sürümlerde MultiIndex döndürüyor (Ticker -> Price Type)
        if isinstance(df_w.columns, pd.MultiIndex):
             # Eğer sadece bir sembol indirdiysek seviyeyi düşürebiliriz
             try:
                df_w = df_w.xs(symbol, level=1, axis=1)
                df_h = df_h.xs(symbol, level=1, axis=1)
             except:
                 pass # Belki zaten düzgündür veya farklı yapıdadır

        # Basit SMA Hesaplama
        df_w['SMA_50'] = calculate_sma(df_w['Close'], 50)
        
        # NaN kontrolü
        if pd.isna(df_w['SMA_50'].iloc[-1]): return None
            
        trend_up = df_w['Close'].iloc[-1] > df_w['SMA_50'].iloc[-1]

        last_year = df_w.tail(52)
        high_p = last_year['High'].max()
        low_p = last_year['Low'].min()
        fib_0618 = high_p - ((high_p - low_p) * 0.618)
        
        # Destek Kontrolü
        on_support = abs(df_w['Close'].iloc[-1] - fib_0618) <= (df_w['Close'].iloc[-1] * 0.03)

        # --- 3. SAATLİK ANALİZ ---
        df_h['RSI'] = calculate_rsi(df_h['Close'], 14)
        
        if len(df_h['RSI']) < 1: return None
        
        rsi_val = df_h['RSI'].iloc[-1]
        
        if pd.isna(rsi_val): return None
        
        oversold = rsi_val < 35

        # Mum Formasyonu
        open_p = df_h['Open'].iloc[-1]
        close_p = df_h['Close'].iloc[-1]
        high_h = df_h['High'].iloc[-1]
        low_h = df_h['Low'].iloc[-1]
        
        body = abs(close_p - open_p)
        full = high_h - low_h
        
        if full == 0: return None
        
        lower_shadow = min(open_p, close_p) - low_h
        is_reversal = (body <= full * 0.15) or (lower_shadow >= body * 2)

        # --- 4. KARAR ---
        if trend_up and on_support and oversold and is_reversal:
            
            # Hedefler
            stop_loss = low_h * 0.99
            tp1 = high_p
            tp2 = high_p + ((high_p - low_p) * 0.272)
            
            risk = df_h['Close'].iloc[-1] - stop_loss
            reward = tp1 - df_h['Close'].iloc[-1]
            rr = round(reward / risk, 2) if risk > 0 else 0

            return {
                "symbol": symbol,
                "price": round(df_h['Close'].iloc[-1], 2),
                "rsi": round(rsi_val, 2),
                "stop_loss": round(stop_loss, 2),
                "tp1": round(tp1, 2),
                "tp2": round(tp2, 2),
                "rr_ratio": rr,
                "fib_level": round(fib_0618, 2)
            }
            
    except Exception as e:
        # Hata bastırma, ama istenirse loglanabilir
        # print(f"Hata ({symbol}): {e}")
        return None

def main():
    print("Tarama başlatılıyor...")
    sinyaller = []

    for sembol in SEMBOLLER:
        print(f"Analiz ediliyor: {sembol}", end="\r")
        sonuc = analiz_et(sembol)
        if sonuc:
            print(f"\nSinyal bulundu: {sembol}")
            sinyaller.append(sonuc)
            save_to_db(sonuc) # <-- VERİTABANINA KAYDET
        time.sleep(1) # API limitleri için bekleme

    if sinyaller:
        mesaj = "🚨 **ALIM FIRSATI** 🚨\n\n"
        for s in sinyaller:
            mesaj += f"💎 *{s['symbol']}*\n"
            mesaj += f"💵 {s['price']} | RSI: {s['rsi']}\n"
            mesaj += f"🎯 TP1: {s['tp1']} | 🛑 STOP: {s['stop_loss']}\n"
            mesaj += "----------------------\n"
        
        send_telegram(mesaj)
    else:
        print("\nSinyal yok.")

if __name__ == "__main__":
    main()
