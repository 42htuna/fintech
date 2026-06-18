# 📊 FinTech Yatırım Takip ve Enflasyon Muhasebesi Platformu

Bu proje; Borsa İstanbul (BIST), Amerikan Borsaları (US), Avrupa Borsaları (EU) ve Kripto Para (CRYPTO) piyasalarındaki yatırımlarınızı tek bir merkezden yönetmeniz, kümülatif maliyet eğrilerini izlemeniz ve **Sermaye Piyasası Kurulu (SPK) / Gelir İdaresi Başkanlığı (GİB)** uyumlu vergi beyan altyapısı kurmanız için geliştirilmiş Python/Django tabanlı kurumsal bir Fintech platformudur.

---

## 🚀 Öne Çıkan Mühendislik ve Finans Özellikleri

* **Gelişmiş FIFO (First-In, First-Out) Algoritması:** Satış işlemlerinde eldeki ilk alınan varlıklar kuruşu kuruşuna tespit edilerek eritilir. Kalan stoklar veritabanı seviyesinde atomik olarak yönetilir.

* **Enflasyon Düzeltmesi (Yİ-ÜFE):** Satılan varlığın alındığı ayın Yİ-ÜFE endeksi ile güncel endeks kıyaslanarak maliyet enflasyona göre pürüzsüzce revize edilir. Endeks bulunamazsa ana para güvenliği için çarpan `1.00` kabul edilir.

* **Güvenli Mühürleme (FIFO Hash):** FIFO döngüsünün parçaladığı her işlem ve o günkü endeks değerleri benzersiz bir hash (`p_hash`) zinciri ile veritabanına kilitlenir.

* **Çoklu Para Birimi & Otomatik Kur:** Yabancı varlıklar için işlem tarihindeki resmi TCMB gösterge kurları geriye dönük tarama (Max 10 gün) algoritmasıyla otomatik eşleştirilir.

* **Canlı Dashboard & Trend Analizi:** Chart.js entegrasyonu ile kümülatif alış maliyetleri, anlık portföy değeri ve net reel kâr çizgileri dinamik olarak haritalandırılır.

---

## 📦 Güncel Bağımlılıklar (requirements.txt)

Proje, **Python 3.13** ortamında tam kararlılıkla çalışacak şekilde yapılandırılmıştır.

```text
# Temel Geliştirme Framework'ü
Django==6.0.6

# Veritabanı Sürücüsü (PostgreSQL)
psycopg2-binary==2.9.12

# Veri Analizi ve Excel Entegrasyonları
pandas==3.0.3
numpy==2.4.6
openpyxl==3.1.5

# Canlı Finansal Veri ve Kur Servisleri
yfinance==1.4.1
requests==2.34.2
python-dateutil==2.9.0.post0

# Üretim (Production) Ortamı Araçları
waitress==3.0.2
gunicorn==26.0.0
whitenoise==6.12.0

# Yardımcı Metin ve SQL Düzenleyiciler
sqlparse==0.5.5
asgiref==3.11.1

# Çevre Değişkenleri ve Yapılandırma Yönetimi
python-dotenv==1.2.2
```

---

## Kurulum ve Yerel Geliştirme (Local Development)

### 1. Sanal Ortamı Aktif Edin ve Bağımlılıkları Yükleyin

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# Windows için: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Güvenlik Anahtarı (.env) Yapılandırması

Projenin kök dizininde (**settings.py**'nin görebileceği konumda) bir **.env** dosyası oluşturun. Terminalde taze bir anahtar üretip bu dosyaya ekleyin:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

```plaintext
# .env dosyasının içeriği
DJANGO_SECRET_KEY=urettiginiz_gizli_anahtar
```

### 3. Veritabanı Göçleri ve Sunucuyu Başlatma

**migrations** dizini yoksa oluşturmak için:

```bash
python manage.py makemigrations investments
python manage.py makemigrations
```

varsa buradan devam edin:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

⚠️ Kritik Uyarı (DEBUG = False Testi): Yerel ortamda **DEBUG = False** modunu test etmek isterseniz, Django statik dosyaları (CSS/JS) engeller. Tasarımın kırılmaması için yerel sunucuyu **python manage.py runserver --insecure** komutuyla başlatmalısınız.

---

### 4. ⚡ Veri Yükleme ve Senkronizasyon Komutları

Projede **TCMB** kaynaklı döviz kurları ve **Yİ-ÜFE** enflasyon endeks veritabanını beslemek için akıllı dosya kontrol mekanizmasına **(Excel/JSON)** sahip 3 yeni Django yönetim komutu eklenmiştir.

| Komut | Parametreler | Açıklama |
| :--- | :--- | :--- |
| `python manage.py ekle` | `--kur`, `--file [yol]` | Tek bir çatı altından seçimli olarak kur veya endeks yüklemesi yapar. |
| `python manage.py ekle` | `--endeks`, `--file [yol]` | Tek bir çatı altından seçimli olarak kur veya endeks yüklemesi yapar. |
| `python manage.py ekle_kur` | `--file [yol]` | Doğrudan döviz kuru verilerini (`bulk_create` ile) sisteme işler. |
| `python manage.py ekle_endeks` | `--file [yol]` | Doğrudan Yİ-ÜFE enflasyon verilerini (`update_or_create` ile) sisteme işler. |
| `python manage.py add_inflation`  |   `--file [yol]` | Yereldeki (tcmb_enflasyon_verileri.xlsx) dosyasındaki tüm geçmiş Yİ-ÜFE verilerini veritabanına topluca enjekte eder. |
| `python manage.py update_inflation_null`  |   `-` | Yereldeki Excel dosyasından (tcmb_enflasyon_verileri.xlsx) boş veya eksik ayların Yİ-ÜFE verilerini günceller. |
| `python manage.py update_inflation`  |   `-` | TCMB EVDS API'sine bağlanarak canlı veri çekmeye çalışır. Kurumsal IP engeli veya geçersiz API anahtarı durumunda güvenlik gereği işlemi keser. |
| `python manage.py add_forex`  |   `--file [yol]` | Excel tablosundaki resmi TCMB kurlarını sisteme topluca enjekte eder. |
| `python manage.py seed_inflation`  |   `-` | Endeksi seed sözlüğünden manuel olarak sisteme topluca enjekte eder. |

#### 💡 Akıllı Dosya Kontrol (Fallback) Mekanizması

Tüm komutlar hibrit bir dosya doğrulama mimarisine sahiptir:

1. **Excel Varsa:** Sistem öncelikli olarak **`.xlsx`** dosyasını baz alır, verileri yüklerken otomatik olarak geriye dönük bir **`.json`** yedek dosyası üretir.

2. **Excel Yok, JSON Varsa:** Projenin üretim (production) ortamında Excel olmasa dahi, sistem otomatik olarak mevcut **`.json`** yan yolunu (fallback) devreye sokarak veritabanını kesintisiz beslemeye devam eder.

3. **Hiçbiri Yoksa:** Hata vermeden önce ilgili dizinde boş bir **JSON** şablonu oluşturarak kullanıcının veri girmesini kolaylaştırır.

#### Örnek Kullanımlar

```bash
# Akıllı komut ile enflasyon endekslerini yükleme (Varsayılan dosya üzerinden)
python manage.py ekle --endeks

# Akıllı komut ile kur verilerini yükleme (Varsayılan dosya üzerinden)
python manage.py ekle --kur

# Özel bir JSON dosyasından doğrudan kur yükleme yan yolunu tetikleme
python manage.py ekle_kur --file yedekler/tcmb_2026_kur.json

# Doğrudan spesifik bir Excel dosyasından endeks yükleme
python manage.py ekle_endeks --file /path/to/enflasyon.xlsx
```

### 5. 🔄 Veritabanı Yedekleme ve Taşıma (Backup)

Verileri Windows ve Linux ortamları arasında aktarırken Türkçe karakter uyuşmazlıklarını ve sistem veri çakışmalarını önlemek için şu betikler kullanılmalıdır:

#### Veriyi Dışa Aktarma (Yedekleme)

**Windows (PowerShell/CMD):**

```bash
python -Xutf8 manage.py dumpdata --exclude contenttypes --exclude auth.Permission --format json --indent 4 -o database_backup.json
```

**Linux / Mac:**

```bash
python manage.py dumpdata --exclude contenttypes --exclude auth.Permission --indent 4 -o database_backup.json
```

**Veriyi İçe Aktarma (Geri Yükleme):**

```bash
python manage.py loaddata database_backup.json
```

### 6. 🌐 Üretim Ortamı Dağıtımı (Production Deployment)
Uygulama canlıya alınırken settings.py içinde **DEBUG = False** set edilmeli ve dış dünyaya asla Django'nun çekirdek runserver motoruyla açılmamalıdır.

**Adım 1: Statik Dosyaları Derleyin**

```bash
python manage.py collectstatic --noinput
```

**Adım 2: Gunicorn/Waitress Sunucusunu Başlatın**

Dış API **(Yahoo Finance, TCMB)** isteklerindeki olası gecikmeler ve kilitlenmelerin **(Worker Timeout)** önüne geçmek amacıyla eş zamanlı işçiler ve arttırılmış zaman aşımı süresi **($t = 90\text{ sn}$)** ile başlatılması zorunludur:

```bash
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 90
```

```bash
waitress-serve --port=8000 --threads=16 --connection-limit=200 core.wsgi:application
```

⚠️ Not: Windows için en iyi alternatif Waitress'dir.

---

### 7. 🔭 Proje Öngörünümü

![Proje Görünümü](https://github.com/42htuna/fintech/blob/main/investments/static/fintech.png)
