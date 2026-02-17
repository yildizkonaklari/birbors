import yfinance as yf
import pandas_ta as ta
import requests
import os
import pandas as pd

# --- AYARLAR ---
# BIST 30 hisseleri ve Kripto (Örnek liste)
SEMBOLLER = ["THYAO.IS", "ASELS.IS", "GARAN.IS", "SISE.IS", "AKBNK.IS", "BTC-USD", "ETH-USD"]

# Telegram Ayarları (GitHub Secrets'tan alacak)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(message):
    if TELEGRAM_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    else:
        print(message)

def analiz_et(symbol):
    try:
        # 1. VERİ ÇEKME
        # Haftalık Veri (Trend ve Fib için)
        df_w = yf.download(symbol, period="2y", interval="1wk", progress=False)
        # Saatlik Veri (Tetikleyici ve RSI için)
        df_h = yf.download(symbol, period="1mo", interval="1h", progress=False)

        if len(df_w) < 50 or len(df_h) < 14:
            return None

        # 2. ANALİZ: HAFTALIK (BÜYÜK RESİM)
        # Trend: Fiyat 50 haftalık ortalamanın üzerinde mi?
        df_w['SMA_50'] = ta.sma(df_w['Close'], length=50)
        current_price = df_w['Close'].iloc[-1]
        trend_up = current_price > df_w['SMA_50'].iloc[-1]

        # Fibonacci 0.618 (Son 1 yılın en tepe ve en dibine göre)
        # Not: Basitleştirilmiş yaklaşımdır.
        last_year = df_w.tail(52)
        high = last_year['High'].max()
        low = last_year['Low'].min()
        fib_0618 = high - ((high - low) * 0.618)
        
        # Fiyat Fib desteğine %3 yakın mı?
        on_support = abs(current_price - fib_0618) <= (current_price * 0.03)

        # 3. ANALİZ: SAATLİK (TETİKLEYİCİ)
        # RSI < 35 (Aşırı Satım)
        df_h['RSI'] = ta.rsi(df_h['Close'], length=14)
        oversold = df_h['RSI'].iloc[-1] < 35

        # Mum Formasyonu (Doji veya Hammer)
        # Basit Doji Mantığı: Açılış ve Kapanış birbirine çok yakın
        body_size = abs(df_h['Close'].iloc[-1] - df_h['Open'].iloc[-1])
        full_size = df_h['High'].iloc[-1] - df_h['Low'].iloc[-1]
        is_doji = body_size <= (full_size * 0.1) # Gövde, fitilin %10'undan küçükse

        # 4. SONUÇ (CONFLUENCE)
        # Tüm şartlar sağlanıyor mu?
        if trend_up and on_support and oversold and is_doji:
            return {
                "symbol": symbol,
                "price": round(current_price, 2),
                "fib_level": round(fib_0618, 2),
                "rsi": round(df_h['RSI'].iloc[-1], 2)
            }
            
    except Exception as e:
        print(f"Hata ({symbol}): {e}")
        return None

# --- ANA DÖNGÜ ---
print("Tarama Başlıyor...")
bulunanlar = []

for sembol in SEMBOLLER:
    sonuc = analiz_et(sembol)
    if sonuc:
        bulunanlar.append(sonuc)

if bulunanlar:
    mesaj = "🚨 **ALIM SİNYALİ TESPİT EDİLDİ** 🚨\n\n"
    for s in bulunanlar:
        mesaj += f"📈 *{s['symbol']}*\n"
        mesaj += f"💰 Fiyat: {s['price']}\n"
        mesaj += f"Support (Fib 0.618): {s['fib_level']}\n"
        mesaj += f"RSI (1H): {s['rsi']}\n"
        mesaj += "------------------\n"
    
    send_telegram(mesaj)
    print("Sinyal gönderildi.")
else:
    print("Kriterlere uyan hisse bulunamadı.")
