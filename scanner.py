import yfinance as yf
import pandas_ta as ta
import requests
import os
import pandas as pd
import time
from supabase import create_client, Client # YENİ EKLENDİ

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
SUPABASE_URL = os.environ.get("SUPABASE_URL") # YENİ
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") # YENİ

# Supabase İstemcisi
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

def send_telegram(message):
    if TELEGRAM_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Telegram hatası: {e}")

def save_to_db(data):
    """Sinyali veritabanına kaydeder"""
    if supabase:
        try:
            # Veriyi hazırla
            kayit = {
                "symbol": data["symbol"],
                "price": data["price"],
                "rsi": data["rsi"],
                "status": "AL" # Şimdilik sadece AL sinyali üretiyoruz
            }
            # Supabase'e ekle
            supabase.table("signals").insert(kayit).execute()
            print(f"{data['symbol']} veritabanına kaydedildi.")
        except Exception as e:
            print(f"Veritabanı hatası: {e}")

def analiz_et(symbol):
    try:
        # --- 1. VERİ ÇEKME ---
        df_w = yf.download(symbol, period="2y", interval="1wk", progress=False, auto_adjust=True)
        df_h = yf.download(symbol, period="1mo", interval="1h", progress=False, auto_adjust=True)

        if len(df_w) < 50 or len(df_h) < 14: return None

        # --- 2. HAFTALIK ANALİZ ---
        df_w['SMA_50'] = ta.sma(df_w['Close'], length=50)
        
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
        df_h['RSI'] = ta.rsi(df_h['Close'], length=14)
        rsi_val = df_h['RSI'].iloc[-1]
        oversold = rsi_val < 35

        # Mum Formasyonu
        open_p = df_h['Open'].iloc[-1]
        close_p = df_h['Close'].iloc[-1]
        high_h = df_h['High'].iloc[-1]
        low_h = df_h['Low'].iloc[-1]
        
        body = abs(close_p - open_p)
        full = high_h - low_h
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
        return None

def main():
    print("Tarama başlatılıyor...")
    sinyaller = []

    for sembol in SEMBOLLER:
        sonuc = analiz_et(sembol)
        if sonuc:
            sinyaller.append(sonuc)
            save_to_db(sonuc) # <-- VERİTABANINA KAYDET
        time.sleep(1)

    if sinyaller:
        mesaj = "🚨 **ALIM FIRSATI** 🚨\n\n"
        for s in sinyaller:
            mesaj += f"💎 *{s['symbol']}*\n"
            mesaj += f"💵 {s['price']} | RSI: {s['rsi']}\n"
            mesaj += f"🎯 TP1: {s['tp1']} | 🛑 STOP: {s['stop_loss']}\n"
            mesaj += "----------------------\n"
        
        send_telegram(mesaj)
    else:
        print("Sinyal yok.")

if __name__ == "__main__":
    main()
