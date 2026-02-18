# Birbors - BIST 50 Algoritmik Tarayıcı 📈

Birbors, BIST 50 hisselerini teknik analiz yöntemleriyle tarayan ve potansiyel alım fırsatlarını belirleyen bir araçtır. Python tabanlı tarayıcı ve sinyalleri görüntülemek için bir HTML dashboard içerir.

## Özellikler ✨

### 1. Teknik Analiz Tarayıcısı (`scanner.py`)
Python scripti, Yahoo Finance üzerinden veri çeker ve aşağıdaki stratejiye göre hisseleri analiz eder:
-   **Trend Takibi**: Fiyat, 50 haftalık Hareketli Ortalamanın (SMA 50) üzerinde olmalıdır.
-   **Fibonacci Geri Çekilmesi**: Fiyat, son 52 haftanın zirvesinden hesaplanan 0.618 Fibonacci seviyesine yakın (destek bölgesinde) olmalıdır.
-   **Aşırı Satım (Oversold)**: Saatlik RSI değeri 35'in altında olmalıdır.
-   **Dönüş Formasyonu**: Saatlik grafikte dönüş mum formasyonu (Hammer, Doji vb.) aranır.

### 2. Dashboard (`index.html`)
Tarayıcı sonuçlarını ve portföyünüzü takip edebileceğiniz modern bir arayüzdür.
-   **Canlı Sinyaller**: Supabase veritabanından gelen son sinyalleri listeler.
-   **Portföy Yönetimi**: Kendi takip listenizi oluşturabilir ve tarayıcıya entegre edebilirsiniz (Manuel eklenebilir).
-   **İstatistikler**: Toplam takip edilen hisse, sinyal sayısı ve hata durumlarını gösterir.

## Kurulum 🛠️

1.  Repository'i klonlayın:
    ```bash
    git clone https://github.com/yildizkonaklari/birbors.git
    cd birbors
    ```

2.  Gerekli kütüphaneleri yükleyin:
    ```bash
    pip install -r requirements.txt
    ```

## Kullanım 🚀

### Tarayıcıyı Çalıştırma
Tarayıcıyı başlatmak için terminalde şu komutu çalıştırın:
```bash
python scanner.py
```
Script, BIST 50 listesindeki hisseleri sırayla analiz eder. Eğer bir alım fırsatı bulursa:
-   Konsola yazdırır.
-   Telegram üzerinden bildirim gönderir (Ayarlıysa).
-   Supabase veritabanına kaydeder (Ayarlıysa).

### Dashboard'u Açma
`index.html` dosyasını bir web tarayıcısında açarak sinyalleri takip edebilirsiniz.

## Konfigürasyon (Opsiyonel) ⚙️

Telegram bildirimleri ve Veritabanı kaydı için aşağıdaki ortam değişkenlerini ayarlayabilirsiniz:

-   `TELEGRAM_TOKEN`: Telegram Bot Token
-   `CHAT_ID`: Telegram Kanal/Grup ID
-   `SUPABASE_URL`: Supabase Proje URL
-   `SUPABASE_KEY`: Supabase API Key

Eğer bu değişkenler ayarlanmazsa, script sadece konsola çıktı verir (Dry Run modu).

## Lisans 📄
Bu proje açık kaynaklıdır ve eğitim amaçlıdır. Yatırım tavsiyesi değildir.
