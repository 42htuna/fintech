import json
import codecs
import csv
from django.shortcuts import render
from django.db.models import Sum
from django.http import HttpResponse
from datetime import timedelta
from decimal import Decimal
from .models import Asset, Transaction, Sale, InflationIndex
from .services import get_live_data

def portfolio_dashboard(request):
        
    assets = Asset.objects.all()
    hisse_listesi = []
    kripto_listesi = []
    
    # 1. ÜST ÖZET DEĞİŞKENLERİ (Decimal hassasiyeti ile başlatıldı)
    total_maliyet = Decimal('0.00')
    total_reel_maliyet = Decimal('0.00')
    total_portfoy_degeri = Decimal('0.00')
    total_kar_zarar = Decimal('0.00')
    total_reel_getiri = Decimal('0.00')
    total_kalkan_tl = Decimal('0.00')

    # En güncel endeksi çek
    latest_index_obj = InflationIndex.objects.order_by('-year', '-month').first()
    latest_index = latest_index_obj.value if latest_index_obj else Decimal('1.00')

    # TEK ANA DÖNGÜ: Tüm hesaplamalar tek seferde yapılır
    for asset in assets:
        stocks = Transaction.objects.filter(asset=asset, transaction_type='BUY', remaining_quantity__gt=0)
        total_qty = sum(s.remaining_quantity for s in stocks)
        if total_qty <= 0: 
            continue

        # Canlı Veri Çek
        try:
            live_price, live_exchange_rate = get_live_data(asset.symbol, asset.asset_type)
            
        except:
            live_price, live_exchange_rate = Decimal('0.00'), Decimal('1.00')

        ham_maliyet_tl = Decimal('0.00')
        endekslenmis_maliyet_tl = Decimal('0.00')

        # Stok kırılımlarını dön ve endeksle
        for s in stocks:
            alis_maliyet_tl = s.remaining_quantity * s.price_foreign * s.exchange_rate
            ham_maliyet_tl += alis_maliyet_tl

            # NoneType güvenlik kontrolü
            buy_index = s.yi_ufe_index if (s.yi_ufe_index is not None and s.yi_ufe_index > 0) else Decimal('1.00')

            multiplier = latest_index / buy_index
            actual_multiplier = multiplier if multiplier >= Decimal('1.10') else Decimal('1.00')
            endekslenmis_maliyet_tl += alis_maliyet_tl * actual_multiplier

        guncel_fiyat_tl = (live_price * live_exchange_rate).quantize(Decimal('0.01'))
        guncel_deger_tl = (total_qty * live_price * live_exchange_rate).quantize(Decimal('0.01'))
        kar_zarar = guncel_deger_tl - ham_maliyet_tl
        performans = ((guncel_deger_tl / ham_maliyet_tl) - 1) * 100 if ham_maliyet_tl > 0 else 0
        reel_kar = guncel_deger_tl - endekslenmis_maliyet_tl
        vergi_kalkani = endekslenmis_maliyet_tl - ham_maliyet_tl
        
        # --- LÜZUMSUZ DÖNGÜLERİ SİLEN SİHİRLİ DOKUNUŞ: KÜMÜLATİF TOPLAMA ---
        total_maliyet += ham_maliyet_tl
        total_reel_maliyet += endekslenmis_maliyet_tl
        total_portfoy_degeri += guncel_deger_tl
        total_kar_zarar += kar_zarar
        total_reel_getiri += reel_kar
        total_kalkan_tl += vergi_kalkani

        item = {
            'symbol': asset.symbol,
            'name': asset.name,
            'asset_type': asset.get_asset_type_display(),
            'qty': total_qty,
            'ham_maliyet': ham_maliyet_tl,
            'guncel_fiyat': guncel_fiyat_tl,
            'guncel_deger': guncel_deger_tl,
            'kar_zarar': kar_zarar,
            'performans': performans,
            'vergi_kalkani': vergi_kalkani,
            'reel_kar': reel_kar,
        }

        if asset.asset_type == 'CRYPTO':
            kripto_listesi.append(item)
        else:
            hisse_listesi.append(item)
            
    # Dağılım Grafiği Verisi Hazırlığı
    all_items = hisse_listesi + kripto_listesi
    labels = [i['symbol'] for i in all_items]
    values = [float(i['guncel_deger']) for i in all_items]

    # ==============================================================================
    # FIFO/Satış Sistemi - KÜMÜLATİF (YIĞILMALI) GRAFİK DESTEKLİ DECIMAL ALGORİTMASI
    # ==============================================================================
    sales_data_queryset = Sale.objects.all().select_related('asset').order_by('sale_date')
    
    line_labels = []
    alis_maliyetleri = []
    endeksli_maliyetler = []
    satislar = []
    net_satislar = []
    final_sales_list = []

    latest_index_obj = InflationIndex.objects.order_by('-year', '-month').first()
    system_latest_index = latest_index_obj.value if latest_index_obj else Decimal('1.00')

    # Kümülatif Toplam Sayaçları (Decimal)
    cum_alis_maliyeti = Decimal('0.00')
    cum_endeksli_maliyet = Decimal('0.00')
    cum_satis_tutari = Decimal('0.00')
    cum_reel_kar_zarar = Decimal('0.00')

    def clean_decimal(value_str, fallback="0.00"):
        if not value_str:
            return Decimal(fallback)
        s = str(value_str).strip().replace('\xa0', '').replace(' ', '')
        if '.' in s and ',' in s:
            if s.find('.') < s.find(','):
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')
        else:
            if ',' in s:
                s = s.replace(',', '.')
        try:
            return Decimal(s)
        except:
            return Decimal(fallback)

    for s in sales_data_queryset:
        try:
            sale_date = s.sale_date
            asset_symbol = s.asset.symbol if (s.asset and hasattr(s.asset, 'symbol')) else str(s.asset)
            
            # 1. ADIM: Satış Verileri ve Satış Komisyonu (Döviz bazlı)
            quantity = Decimal(str(s.quantity if s.quantity else 0))
            sale_price_foreign = Decimal(str(getattr(s, 'sale_price_foreign', 0) or 0))
            sale_commission_foreign = Decimal(str(getattr(s, 'sale_commission_foreign', 0) or 0))
            sale_exchange_rate = Decimal(str(getattr(s, 'sale_exchange_rate', 1) or 1))
            
            # Kur öncesi komisyon düşülüp TL'ye çevrilen Net Satış Tutarı
            satis_tl = ((quantity * sale_price_foreign) - sale_commission_foreign) * sale_exchange_rate

            # 2. ADIM: Hash Parçalayarak Alış Verilerini Çekme (Döviz bazlı)
            tx_hash = getattr(s, 'purchase_hash', None)
            
            alis_fiyati_orj = sale_price_foreign
            alis_komisyon_orj = Decimal('0.00')
            alis_kuru_orj = sale_exchange_rate
            alis_yi_ufe_orj = Decimal('1.00')

            if tx_hash and '|' in str(tx_hash):
                parts = str(tx_hash).split('|')
                if len(parts) >= 5:
                    alis_fiyati_orj = clean_decimal(parts[1])
                    alis_komisyon_orj = clean_decimal(parts[2])
                    alis_kuru_orj = clean_decimal(parts[3], fallback="1.00")
                    alis_yi_ufe_orj = clean_decimal(parts[4], fallback="1.00")

            # 3. ADIM: Maliyet ve Endeksleme Hesapları (TL)
            alis_maliyet_tl = ((quantity * alis_fiyati_orj) + alis_komisyon_orj) * alis_kuru_orj

            if alis_yi_ufe_orj > 0:
                multiplier = system_latest_index / alis_yi_ufe_orj
                actual_multiplier = multiplier if multiplier >= Decimal('1.10') else Decimal('1.00')
            else:
                actual_multiplier = Decimal('1.00')
            
            endeksli_maliyet_tl = alis_maliyet_tl * actual_multiplier
            net_satis_tl = satis_tl - endeksli_maliyet_tl

            # 4. ADIM: KÜMÜLATİF TOPLAMLARI GÜNCELLEME (Üstüne ekleyerek gidiyoruz)
            cum_alis_maliyeti += alis_maliyet_tl
            cum_endeksli_maliyet += endeksli_maliyet_tl
            cum_satis_tutari += satis_tl
            cum_reel_kar_zarar += net_satis_tl

            # Grafik dizilerine kümülatif değerleri float olarak paslıyoruz
            if sale_date:
                line_labels.append(sale_date.strftime('%d-%m-%Y'))
            else:
                line_labels.append("-")
                
            alis_maliyetleri.append(float(round(cum_alis_maliyeti, 2)))
            endeksli_maliyetler.append(float(round(cum_endeksli_maliyet, 2)))
            satislar.append(float(round(cum_satis_tutari, 2)))
            net_satislar.append(float(round(cum_reel_kar_zarar, 2)))

            # Tabloda ise her satırın kendi özgün değerini görmeye devam edelim (Doğru analiz için)
            final_sales_list.append({
                'db_date': sale_date,
                'db_asset_symbol': asset_symbol,
                'db_quantity': float(quantity),                
                'calc_purchase_value': float(round(alis_maliyet_tl, 2)),
                'calc_indexed_purchase': float(round(endeksli_maliyet_tl, 2)),
                'calc_sale_value': float(round(satis_tl, 2)),
                'calc_net_profit': float(round(net_satis_tl, 2)),
            })
        except Exception as e:
            print(f"Kümülatif Hesaplama Hatası: {str(e)}")
            
    try:
        _, usd_kur = get_live_data('USD', 'FOREX')
    except:
        usd_kur = Decimal('1.00')

    try:
        _, eur_kur = get_live_data('EUR', 'FOREX')
    except:
        eur_kur = Decimal('1.00')

    context = {
        'hisse_listesi': hisse_listesi,
        'kripto_listesi': kripto_listesi,
        'usd_kur': usd_kur,
        'eur_kur': eur_kur,
        'total_kalkan': total_kalkan_tl,
        'total_maliyet': total_maliyet,
        'total_reel_maliyet': total_reel_maliyet,
        'total_portfoy_degeri': total_portfoy_degeri,
        'total_kar_zarar': total_kar_zarar,
        'total_reel_getiri': total_reel_getiri,
        'chart_labels': json.dumps(labels),
        'chart_values': json.dumps(values),        
        'sales_data': final_sales_list,        
        'line_labels': json.dumps(line_labels),
        'alis_maliyetleri': json.dumps(alis_maliyetleri),
        'endeksli_maliyetler': json.dumps(endeksli_maliyetler),
        'satislar': json.dumps(satislar),
        'net_satislar': json.dumps(net_satislar),
    }
    return render(request, 'dashboard.html', context)

# URL Hatasını Çözen Fonksiyon İsmi (AttributeError Fix)
def export_sales_csv(request):

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="vergi_beyan.csv"'

    response.write(codecs.BOM_UTF8)

    writer = csv.writer(response, delimiter=';')

    writer.writerow([
        'No',
        'Alış İşlem Kodu (Hash)',
        'Tarih',
        'Hisse',
        'Lot',
        'Fiyat',
        'Komisyon',
        'Para Birimi',
        'TCMB Kur',
        'Yİ-ÜFE'
    ])

    sales = Sale.objects.all().order_by('sale_date')
 
    include_bist = False  # False yaparsan BIST hariç tutulur
    include_cr = False  # False yaparsan CRYPTO hariç tutulur    

    for i, s in enumerate(sales, start=1):

        if not include_bist and s.asset.asset_type == "BIST" or not include_cr and s.asset.asset_type == "CRYPTO":
            continue

        if s.asset.asset_type == "BIST":
            currency = "TL"
        elif s.asset.asset_type in ["US", "CRYPTO"]:
            currency = "USD"
        else:
            currency = "EUR"

        writer.writerow([
            i,
            s.purchase_hash,
            s.sale_date.strftime('%d/%m/%Y'),
            s.asset.symbol,
            s.quantity,
            s.sale_price_foreign,
            s.sale_commission_foreign,
            currency,
            s.sale_exchange_rate,
            s.sale_index
        ])

    return response
