import yfinance as yf
import pandas_ta as ta
import requests
import os
import pandas as pd
import time

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

# GitHub Secrets'tan alınacak değişkenler
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(message):
    """Telegram'a mesaj gönderen fonksiyon"""
    if TELEGRAM_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Telegram hatası: {e}")
    else:
        print("Telegram ayarları eksik! Mesaj konsola yazılıyor:")
        print(message)

def analiz_et(symbol):
    """Tek bir sembol için tüm stratejiyi çalıştırır"""
    try:
        # --- 1. VERİ ÇEKME ---
        # Haftalık Veri (Trend ve Büyük Destekler için)
        df_w = yf.download(symbol, period="2y", interval="1wk", progress=False, auto_adjust=True)
        
        # Saatlik Veri (Giriş Sinyali ve RSI için)
        df_h = yf.download(symbol, period="1mo", interval="1h", progress=False, auto_adjust=True)

        # Veri kontrolü (Yeterli veri yoksa atla)
        if len(df_w) < 50 or len(df_h) < 14:
            return None

        # --- 2. HAFTALIK ANALİZ (BÜYÜK RESİM) ---
        
        # A) Trend Kontrolü: Fiyat > 50 Haftalık SMA
        df_w['SMA_50'] = ta.sma(df_w['Close'], length=50)
        current_w_close = df_w['Close'].iloc[-1]
        
        # Eğer SMA hesaplanamadıysa (NaN), işlem yapma
        if pd.isna(df_w['SMA_50'].iloc[-1]):
            return None
            
        trend_up = current_w_close > df_w['SMA_50'].iloc[-1]

        # B) Fibonacci 0.618 Desteği
        # Son 52 haftanın (1 yıl) en yükseği ve en düşüğü baz alınır
        last_year = df_w.tail(52)
        high_price = last_year['High'].max()
        low_price = last_year['Low'].min()
        
        # Fib 0.618 Seviyesi: Tepe - ((Tepe - Dip) * 0.618)
        fib_0618 = high_price - ((high_price - low_price) * 0.618)
        
        # Fiyat bu desteğe %3 toleransla yakın mı?
        # Fiyatın fib seviyesinin biraz üstünde veya çok az altında olması kabuldür.
        dist_to_fib = abs(current_w_close - fib_0618)
        on_support = dist_to_fib <= (current_w_close * 0.03)

        # --- 3. SAATLİK ANALİZ (TETİKLEYİCİ) ---
        
        current_price = df_h['Close'].iloc[-1]
        
        # C) RSI Aşırı Satım (< 35)
        df_h['RSI'] = ta.rsi(df_h['Close'], length=14)
        rsi_val = df_h['RSI'].iloc[-1]
        oversold = rsi_val < 35

        # D) Mum Formasyonu (Doji veya Çekiç Benzeri)
        open_p = df_h['Open'].iloc[-1]
        close_p = df_h['Close'].iloc[-1]
        high_p = df_h['High'].iloc[-1]
        low_p = df_h['Low'].iloc[-1]
        
        body_size = abs(close_p - open_p)
        full_size = high_p - low_p
        
        # Gövde tüm mumun %15'inden küçükse (Doji/Kararsızlık)
        # VEYA Alt fitil çok uzunsa (Çekiç/Hammer etkisi - Alıcı geldi demek)
        lower_shadow = min(open_p, close_p) - low_p
        is_reversal_candle = (body_size <= full_size * 0.15) or (lower_shadow >= body_size * 2)

        # --- 4. KARAR VE HEDEF HESAPLAMA ---
        
        # Tüm şartlar sağlanıyor mu?
        # (Trend Yukarı VE Destekte VE RSI Dipte VE Dönüş Mumu Var)
        if trend_up and on_support and oversold and is_reversal_candle:
            
            # --- HEDEF FİYATLAR ---
            
            # Stop Loss: Mumun en düşüğünün %1 altı (Tolerans payı)
            stop_loss = low_p * 0.99
            
            # TP1 (Güvenli Liman): Haftalık grafikteki son tepe (Düşüşün başladığı yer değil, son Swing High)
            # Basitlik adına son 52 haftanın zirvesini veya o anki fib range'in tepesini alıyoruz.
            take_profit_1 = high_price 
            
            # TP2 (Yüksek Kazanç): Fibonacci Extension 0.272 (Trend devam ederse gideceği yer)
            # Formül: Tepe + ((Tepe - Dip) * 0.272)
            fib_extension = high_price + ((high_price - low_price) * 0.272)
            take_profit_2 = fib_extension
            
            # Risk / Kazanç Oranı (TP1'e göre)
            potential_risk = current_price - stop_loss
            potential_reward = take_profit_1 - current_price
            
            if potential_risk > 0:
                rr_ratio = round(potential_reward / potential_risk, 2)
            else:
                rr_ratio = 0

            return {
                "symbol": symbol,
                "price": round(current_price, 2),
                "rsi": round(rsi_val, 2),
                "stop_loss": round(stop_loss, 2),
                "tp1": round(take_profit_1, 2),
                "tp2": round(take_profit_2, 2),
                "rr_ratio": rr_ratio,
                "fib_level": round(fib_0618, 2)
            }
            
    except Exception as e:
        # Hata olursa kodu durdurma, sadece yazdır ve devam et
        # print(f"Hata ({symbol}): {e}") 
        return None

# --- ANA DÖNGÜ ---
def main():
    print("Tarama başlatılıyor...")
    sinyaller = []

    for sembol in SEMBOLLER:
        sonuc = analiz_et(sembol)
        if sonuc:
            sinyaller.append(sonuc)
        time.sleep(1) # Yahoo Finance'i kızdırmamak için küçük bekleme

    if sinyaller:
        mesaj = "🚨 **ALIM FIRSATI (LONG)** 🚨\n"
        mesaj += "Strateji: Trend + Fib 0.618 + RSI + Doji\n\n"
        
        for s in sinyaller:
            mesaj += f"💎 *{s['symbol']}*\n"
            mesaj += f"💵 Giriş: {s['price']}\n"
            mesaj += f"----------------------\n"
            mesaj += f"🛑 Stop Loss: {s['stop_loss']}\n"
            mesaj += f"🎯 Hedef 1 (Tepe): {s['tp1']}\n"
            mesaj += f"🚀 Hedef 2 (Ext): {s['tp2']}\n"
            mesaj += f"----------------------\n"
            mesaj += f"📊 RSI: {s['rsi']} | R/R: 1:{s['rr_ratio']}\n"
            mesaj += f"ℹ️ Fib Desteği: {s['fib_level']}\n\n"
        
        send_telegram(mesaj)
        print("Sinyaller Telegram'a gönderildi.")
    else:
        print("Bu taramada uygun formasyon bulunamadı.")

if __name__ == "__main__":
    main()
