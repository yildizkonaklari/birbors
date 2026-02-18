import yfinance as yf
import pandas as pd
import requests
import warnings

# --- SSL VE PROXY FIX (AGGRESSIVE) ---
from requests.packages.urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
warnings.filterwarnings("ignore")

_original_session = requests.Session
class CustomSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.verify = False; self.trust_env = False
        self.headers.update({
             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
    def request(self, method, url, *args, **kwargs):
        kwargs.setdefault('verify', False)
        return super().request(method, url, *args, **kwargs)
requests.Session = CustomSession
import yfinance.shared as shared
if hasattr(shared, '_create_session'): shared._create_session = lambda: CustomSession()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_sma(series, period=50):
    return series.rolling(window=period).mean()

def check_stock(symbol):
    print(f"\n--- ANALİZ: {symbol} ---")
    try:
        # Veri Çekme
        df_w = yf.download(symbol, period="2y", interval="1wk", progress=False, auto_adjust=True)
        df_h = yf.download(symbol, period="1mo", interval="1h", progress=False, auto_adjust=True)

        if len(df_w) < 50:
            print(f"Yetersiz Haftalık Veri: {len(df_w)}")
            return
            
        print(f"Veri Çekildi. Haftalık: {len(df_w)}, Saatlik: {len(df_h)}")
        
        # Sütun İsimlerini Düzeltme (MultiIndex)
        try:
            # yfinance bazen (Price, Ticker) formatında döner.
            # Sütunlarda 'Close' varsa düzgündür, yoksa Ticker seviyesine inmeye çalışırız.
            if 'Close' not in df_w.columns:
                 # Çok katmanlı mı?
                 if isinstance(df_w.columns, pd.MultiIndex):
                     # Sadece ilk seviyede (Price) 'Close' var mı diye bakmak yerine direkt xs deneyelim
                     # Ancak tek ticker indirince bazen seviye ismi Ticker oluyor.
                     # Basitçe: Eğer Ticker ismi sütunlarda geçiyorsa:
                     pass
        except Exception as e:
            print(f"Veri formatlama uyarısı: {e}")

        # Basit SMA
        # Tek boyutluya indirgeme (Eğer (Price, Ticker) ise)
        if isinstance(df_w.columns, pd.MultiIndex):
             # Bu durumda kolonları düzleştirmek veya xs kullanmak lazım
             # xs kullanılırsa warning verebilir. iloc ile alalım.
             # En güvenlisi: 'Close' sütununu alırken squeeze() yapmak.
             close_w = df_w.iloc[:, df_w.columns.get_level_values(0)=='Close']
             if close_w.shape[1] == 1:
                 df_w = pd.DataFrame({'Close': close_w.iloc[:,0]})
                 # Diğerlerini de almamız lazım ama şimdilik Close yeterli trend için
             else:
                 print("MultiIndex yapısı beklenenden farklı.")
        
        # Güncel yfinance genellikle:
        #              Close    High     Low ...
        # Ticker
        # SYMBOL       10.5     11.0     ...
        # Ancak tek ticker indirince bazen düz döner.
        
        # Son Close değerini alalım
        current_price = df_w['Close'].iloc[-1]
        try:
            current_price = float(current_price.item()) # Eğer series dönerse
        except:
            pass
            
        sma50 = df_w['Close'].rolling(window=50).mean().iloc[-1]
        try:
            sma50 = float(sma50.item())
        except:
            pass

        print(f"Fiyat: {current_price:.2f}")
        print(f"SMA 50: {sma50:.2f}")
        
        trend_up = current_price > sma50
        print(f"1. Yükseliş Trendinde mi? (Fiyat > SMA50): {'EVET' if trend_up else 'HAYIR'}")

        # Fibonacci
        last_year = df_w.tail(52)
        # High/Low tek değer olmalı
        high_p = last_year['High'].max()
        low_p = last_year['Low'].min()
        try: high_p = float(high_p.item())
        except: pass
        try: low_p = float(low_p.item())
        except: pass
            
        fib_0618 = high_p - ((high_p - low_p) * 0.618)
        
        diff = abs(current_price - fib_0618)
        limit = current_price * 0.03
        on_support = diff <= limit
        
        print(f"Fib 0.618 Seviyesi: {fib_0618:.2f}")
        print(f"2. Destek Bölgesinde mi? (Fark < %3): {'EVET' if on_support else 'HAYIR'} (Fark: {diff:.2f}, Limit: {limit:.2f})")

        # RSI
        # Saatlik veri kontrolü
        if isinstance(df_h.columns, pd.MultiIndex):
             close_h = df_h.iloc[:, df_h.columns.get_level_values(0)=='Close']
             if close_h.shape[1] == 1:
                 df_h = pd.DataFrame({'Close': close_h.iloc[:,0], 'Open': df_h.iloc[:, df_h.columns.get_level_values(0)=='Open'].iloc[:,0], 'High': df_h.iloc[:, df_h.columns.get_level_values(0)=='High'].iloc[:,0], 'Low': df_h.iloc[:, df_h.columns.get_level_values(0)=='Low'].iloc[:,0]})

        rsi_series = calculate_rsi(df_h['Close'], 14)
        if len(rsi_series) > 0:
            rsi_val = rsi_series.iloc[-1]
            print(f"Saatlik RSI: {rsi_val:.2f}")
            oversold = rsi_val < 35
            print(f"3. Aşırı Satımda mı? (RSI < 35): {'EVET' if oversold else 'HAYIR'}")
            
            # Formasyon
            open_p = df_h['Open'].iloc[-1]
            close_p = df_h['Close'].iloc[-1]
            high_h = df_h['High'].iloc[-1]
            low_h = df_h['Low'].iloc[-1]
            
            body = abs(close_p - open_p)
            full = high_h - low_h
            
            if full > 0:
                lower_shadow = min(open_p, close_p) - low_h
                is_reversal = (body <= full * 0.15) or (lower_shadow >= body * 2)
                print(f"4. Dönüş Formasyonu Var mı? (Doji/Çekiç): {'EVET' if is_reversal else 'HAYIR'}")
            else:
                 print("4. Dönüş Formasyonu: Veri hatası (H/L 0)")

    except Exception as e:
        print(f"HATA OLUŞTU: {e}")
        import traceback
        traceback.print_exc()

# Örnek birkaç hisse deneyelim
check_stock("THYAO.IS")
check_stock("GARAN.IS")
check_stock("KCHOL.IS")
check_stock("ASELS.IS")
