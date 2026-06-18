import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd
import requests
from django.conf import settings
from django.db import IntegrityError, models, transaction

from .models import IndicativeExchangeRate, InflationIndex, Sale, Transaction

@transaction.atomic
def execute_fifo_sale(asset, sell_qty, sell_px_foreign, s_date, s_kur, s_comm=0):
    sell_qty = Decimal(str(sell_qty))
    
    total_available = Transaction.objects.filter(
        asset=asset, 
        transaction_type='BUY', 
        remaining_quantity__gt=0
    ).aggregate(total=models.Sum('remaining_quantity'))['total'] or Decimal('0')

    EPSILON = Decimal('0.00000001')
    if total_available + EPSILON < sell_qty:
        raise ValueError(f"Yetersiz stok! Mevcut: {total_available}, İstenen: {sell_qty}")

    purchases = Transaction.objects.filter(
        asset=asset,
        transaction_type='BUY',
        remaining_quantity__gt=0
    ).order_by('date', 'id')

    rem = Decimal(str(sell_qty))

    for p in purchases:
        if rem <= 0: break

        take = p.remaining_quantity if p.remaining_quantity <= rem else rem

        if p.yi_ufe_index is not None:
            p_idx_val = p.yi_ufe_index
        else:
            try:
                p_m1_date = p.date.replace(day=1) - timedelta(days=1)
                p_idx_obj = InflationIndex.objects.get(year=p_m1_date.year, month=p_m1_date.month)
                p_idx_val = p_idx_obj.value
            except InflationIndex.DoesNotExist:
                p_idx_val = Decimal('0.00')

        try:
            s_m1_date = s_date.replace(day=1) - timedelta(days=1)
            s_idx_obj = InflationIndex.objects.get(year=s_m1_date.year, month=s_m1_date.month)
            s_idx_val = s_idx_obj.value
        except InflationIndex.DoesNotExist:
            s_idx_val = Decimal('0.00')

        p_hash = f"{p.date.strftime('%d/%m/%Y')}|{p.price_foreign}|{p.commission_foreign}|{p.exchange_rate}|{p_idx_val}"

        try:
            Sale.objects.create(
                asset=asset,
                sale_date=s_date,
                quantity=take,
                sale_price_foreign=Decimal(str(sell_px_foreign)),
                sale_commission_foreign=Decimal(str(s_comm)),
                sale_exchange_rate=Decimal(str(s_kur)),
                purchase_hash=p_hash,
                sale_index=s_idx_val
            )
        except IntegrityError as e:
            raise ValueError(f"Mükerrer Satış kaydı engellendi: {e}")

        # 3. Stoktan düş
        p.remaining_quantity = max(Decimal('0'), p.remaining_quantity - take)
        p.save(update_fields=['remaining_quantity'])
        rem -= take

    if rem > 0:
        raise ValueError(f"Hata: Elinizde yeterli stok yok! Eksik miktar: {rem}")

def fill_missing_inflation_values():
    """Mevcut veritabanında value alanı NULL olan endeksleri Excel'den tamamlar."""
    file_path = f"{settings.BASE_DIR}/tcmb_enflasyon_verileri.xlsx"
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()
    df['Tarih'] = pd.to_datetime(df['Tarih']).dt.strftime('%Y-%m')    

    qs = InflationIndex.objects.filter(value__isnull=True)
    updated = 0

    for obj in qs:
        try:
            key = f"{obj.year}-{obj.month:02d}"
            row = df[df['Tarih'] == key]

            if row.empty:
                continue

            value = row.iloc[0]['Yİ_UFE_Endeks']
            if pd.isna(value):
                continue

            obj.value = Decimal(str(value).replace(',', '.'))
            obj.save(update_fields=['value'])
            updated += 1

        except Exception as e:
            print(f"Hata: {e}")
            continue
            
    return updated

def excel_den_enflasyon_yukle(dosya_yolu):
    """Excel'deki tüm endeks verilerini SQLite sayacını patlatmadan hızlıca bulk_create ile enjekte eder."""
    df = pd.read_excel(dosya_yolu)
    df.columns = df.columns.str.strip()
    df['Tarih'] = pd.to_datetime(df['Tarih']).dt.strftime('%Y-%m')  
    
    mevcut_endeksler = set(InflationIndex.objects.values_list('year', 'month'))
    kayitlar = []

    for _, row in df.iterrows():
        if pd.isna(row['Tarih']):
            continue

        try:
            yil, ay = map(int, str(row['Tarih']).split('-'))
            
            if (yil, ay) in mevcut_endeksler:
                continue

            deger = row['Yİ_UFE_Endeks']
            if pd.isna(deger):
                continue

            kayitlar.append(
                InflationIndex(
                    year=yil,
                    month=ay,
                    value=Decimal(str(deger).replace(',', '.'))
                )
            )
        except Exception as e:
            print(f"Hata: {e}")
            continue

    if kayitlar:
        InflationIndex.objects.bulk_create(kayitlar)
        print(f"✅ {len(kayitlar)} adet yeni enflasyon verisi yüklendi.")
    else:
        print("ℹ️ Yüklenecek endeks verisi bulunamadı, veritabanı zaten güncel!")

def excel_den_kur_yukle(dosya_yolu):
    """Excel'deki kur verilerini SQLite sayacını patlatmadan hızlıca bulk_create ile enjekte eder."""
    df = pd.read_excel(dosya_yolu)
    df.columns = df.columns.str.strip()

    mevcut_tarihler = set(IndicativeExchangeRate.objects.values_list('date', flat=True))
    kayitlar = []

    for _, row in df.iterrows():
        if pd.isna(row['Tarih']):
            continue

        target_date = pd.to_datetime(row['Tarih'], dayfirst=True).date()

        if target_date in mevcut_tarihler:
            continue

        usd_raw = row['USD/TRY']
        eur_raw = row['EUR/TRY']

        if pd.isna(usd_raw) or pd.isna(eur_raw):
            continue

        kayitlar.append(
            IndicativeExchangeRate(
                date=target_date,
                usd_forex_buying=Decimal(str(usd_raw).replace(',', '.')),
                eur_forex_buying=Decimal(str(eur_raw).replace(',', '.'))
            )
        )

    if kayitlar:
        IndicativeExchangeRate.objects.bulk_create(kayitlar)
        print(f"✅ {len(kayitlar)} adet yeni kur verisi başarıyla yüklendi.")
    else:
        print("ℹ️ Yüklenecek kur verisi bulunamadı, veritabanı zaten güncel!")

""" TCMB forex kur sorgulama fonksiyonudur.
İleride belki uygulama içinde kullanılabilir!

python manage.py shell
from investments.utils import get_tcmb_rate
get_tcmb_rate()
get_tcmb_rate('EUR')
get_tcmb_rate('EUR', '15062026')
import datetime as datetime
get_tcmb_rate('EUR', datetime.datetime(2026, 6, 17))
"""
def get_tcmb_rate(currency_code='USD', date=None):
    print(f"get_tcmb_rate() fonksiyonu ile {currency_code} kuru çekiliyor...")
    
    if isinstance(date, str):
        date = datetime.strptime(date, "%d%m%Y")
        
    if date is None:
        date = datetime.now()

    current_date = date

    for _ in range(10):
        if current_date.weekday() == 5: # Cumartesi
            current_date -= timedelta(days=1)
        elif current_date.weekday() == 6: # Pazar
            current_date -= timedelta(days=2)

        date_str = current_date.strftime("%d%m%Y")
        path_str = current_date.strftime("%Y%m")
        url = f"https://www.tcmb.gov.tr/kurlar/{path_str}/{date_str}.xml"
        print(url)
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                for currency in root.findall('Currency'):
                    if currency.get('CurrencyCode') == currency_code:
                        rate = Decimal(currency.find('ForexBuying').text)
                        print(f"{date.strftime("%d.%m.%Y")} tarihinde {currency_code} kuru {rate} TL'dir.")
                        return rate
        except Exception:
            pass

        current_date -= timedelta(days=1)

    print(f"{currency_code} kuru için veri bulunamadı.")
    return None

def get_crypto_rate(symbol, date):
    """
    Binance veya benzeri bir API'den geçmiş tarihli kripto kurunu çeker.
    Şimdilik manuel girdiğin maliyetleri kullanacağız ama bu fonksiyon
    ileride otomatikleşecek.
    """
    pass
