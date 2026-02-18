import yfinance as yf
import requests
import warnings

# SSL Uyarısını Kapat
warnings.filterwarnings("ignore")

print("yfinance version:", yf.__version__)

# SSL Doğrulamasını Devre Dışı Bırakan Session
session = requests.Session()
session.verify = False
session.trust_env = False # Sistem proxy'lerini yok say

# Tarayıcı gibi davran (403/Block yememek için)
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
})

try:
    print("\n--- Testing yf.Ticker (with Session) ---")
    t = yf.Ticker("THYAO.IS", session=session)
    hist = t.history(period="1mo")
    print(hist.head())
    print("Ticker history success!")
except Exception as e:
    print("Ticker history failed:", e)

try:
    print("\n--- Testing yf.download (with Session) ---")
    # yfinance 0.2.xx session parametresini desteklemeyebilir, monkey-patch yapalım
    # Ancak yf.download(..., session=session) destekleniyorsa çalışır.
    
    # Monkey Patch for testing purpose if needed, otherwise try direct
    import yfinance.shared as shared
    shared._create_session = lambda: session
    
    data = yf.download("THYAO.IS", period="1mo", progress=False) # session parametresi bazen çalışmaz
    print(data.head())
    print("Download success!")
except Exception as e:
    print("Download failed:", e)
