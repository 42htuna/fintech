# 📊 FinTech Yatırım Takip ve Enflasyon Muhasebesi Platformu

Bu proje; Borsa İstanbul (BIST), Amerikan Borsaları (US), Avrupa
Borsaları (EU) ve Kripto Para (CRYPTO) piyasalarındaki yatırımlarınızı
tek bir merkezden yönetmeniz, kümülatif maliyet eğrilerini izlemeniz ve
**Sermaye Piyasası Kurulu (SPK) / Gelir İdaresi Başkanlığı (GİB)**
uyumlu vergi beyan altyapısı kurmanız için geliştirilmiş Python/Django
tabanlı kurumsal bir Fintech platformudur.

---

## 🚀 Öne Çıkan Mühendislik ve Finans Özellikleri

* **Gelişmiş FIFO (First-In, First-Out) Algoritması:**
Satış işlemlerinde eldeki ilk alınan varlıklar kuruşu kuruşuna tespit
edilerek eritilir. Kalan stoklar (remaining) veritabanı seviyesinde
atomik olarak yönetilir.

* **Enflasyon Düzeltmesi (Yİ-ÜFE):**
Satılan varlığın alındığı ayın Yİ-ÜFE endeksi ile güncel endeks
kıyaslanarak maliyet enflasyona göre pürüzsüzce revize edilir. Endeks
bulunamazsa ana para güvenliği için çarpan `1.00` kabul edilir.

* **Güvenli Mühürleme (FIFO Hash):**
FIFO döngüsünün parçaladığı her işlem ve o günkü endeks değerleri
benzersiz bir hash (`p_hash`) zinciri ile veritabanına kilitlenir.

* **Çoklu Para Birimi & Otomatik Kur:**
Yabancı varlıklar için işlem tarihindeki resmi TCMB gösterge kurları
geriye dönük tarama (Max 10 gün) algoritmasıyla otomatik eşleştirilir.

* **Canlı Dashboard & Trend Analizi:**
JavaScript tabanlı Chart.js entegrasyonu ile kümülatif alış maliyetleri,
anlık portföy değeri ve net reel kâr çizgileri dinamik olarak
haritalandırılır.

---

## 📦 Güncel Bağımlılıklar (requirements.txt)

Proje, **Python 3.13** ortamında tam kararlılıkla çalışacak şekilde
yapılandırılmıştır. Geliştirme (Local) ve Üretim (Production)
modüllerinin kilitli versiyonları şu şekildedir:

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
```
---

## 🔄 Django dumpdata ve loaddata ile yedekleme (backup.bat/backup.sh):

Verileri Windows ortamından, Linux ortamına aktarırken Türkçe
karakterlerin bozulmaması için **-Xutf8** parametresi ile **UTF8**
karakter kodlaması seçilmelidir.

Boş veritabanına geri yükleme yaparken, veri çakışmalarını ve hataları
önlemek için de **--exclude** parametresi ile **contenttypes** ve
**auth.Permission** tabloları hariç tutulmalıdır.

### Windows ortamında:

```bash
python -Xutf8 manage.py dumpdata --exclude contenttypes --exclude auth.Permission --format json --indent 4 -o database_backup.json
```
```bash
.\backup.bat
```

### Linux ortamında:

```bash
python manage.py dumpdata --exclude contenttypes --exclude auth.Permission --indent 4 -o database_backup.json
```
```bash
bash backup.sh
```
---

### Geri yükleme:

```bash
python manage.py loaddata database_backup.json
```
---
