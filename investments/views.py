import json
import codecs
import csv
import logging
from decimal import Decimal
from django.shortcuts import render
from django.http import HttpResponse
from .services import get_live_data, get_live_data_cached
from .models import Asset, Transaction, Sale, InflationIndex

logger = logging.getLogger(__name__)

def portfolio_dashboard(request):

    assets = Asset.objects.all()
    hisse_listesi = []
    kripto_listesi = []

    total_maliyet = Decimal('0.00')
    total_reel_maliyet = Decimal('0.00')
    total_portfoy_degeri = Decimal('0.00')
    total_kar_zarar = Decimal('0.00')
    total_reel_getiri = Decimal('0.00')
    total_kalkan_tl = Decimal('0.00')

    latest_index = (
        InflationIndex.objects.order_by('-year', '-month')
        .values_list('value', flat=True)
        .first()
        or Decimal('1.00')
    )

    for asset in assets:

        transactions = Transaction.objects.filter(
            transaction_type='BUY',
            remaining_quantity__gt=0
        ).select_related('asset')

        stocks = [t for t in transactions if t.asset_id == asset.id]

        total_qty = sum(s.remaining_quantity for s in stocks)
        if total_qty <= 0:
            continue

        try:
            live_price, live_exchange_rate = get_live_data_cached(
                asset.symbol,
                asset.asset_type,
                asset.currency
            )
        except Exception as e:
            logger.exception(f"Live data error for {asset.symbol}")
            live_price = Decimal('0.00')
            live_exchange_rate = Decimal('1.00')

        ham_maliyet_tl = Decimal('0.00')
        endekslenmis_maliyet_tl = Decimal('0.00')

        for s in stocks:

            cost = ((s.remaining_quantity * s.price_foreign) + s.commission_foreign) * s.exchange_rate
            ham_maliyet_tl += cost

            buy_index = (
                s.yi_ufe_index
                if (s.yi_ufe_index is not None and s.yi_ufe_index > 0)
                else latest_index
            )            

            multiplier = latest_index / buy_index
            multiplier = multiplier if multiplier >= Decimal('1.10') else Decimal('1.00')

            endekslenmis_maliyet_tl += cost * multiplier
       
        if live_price is None or live_price.is_nan():
            live_price = Decimal("0.00")
        
        guncel_tl_fiyat = (live_price * live_exchange_rate).quantize(Decimal('0.01'))
        guncel_deger_tl = (total_qty * guncel_tl_fiyat).quantize(Decimal('0.01'))
        
        if guncel_deger_tl.is_nan():
            guncel_deger_tl = Decimal("0.00")

        kar_zarar = guncel_deger_tl - ham_maliyet_tl

        performans = (
            ((guncel_deger_tl / ham_maliyet_tl) - 1) * 100
            if ham_maliyet_tl > 0 else Decimal("0")
        )

        reel_kar = guncel_deger_tl - endekslenmis_maliyet_tl
        vergi_kalkani = endekslenmis_maliyet_tl - ham_maliyet_tl

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
            'price':live_price,
            'para_birimi': asset.currency,
            'guncel_fiyat': guncel_tl_fiyat,
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

    all_items = hisse_listesi + kripto_listesi
    labels = [i['symbol'] for i in all_items]
    values = [float(i.get('guncel_deger') or 0) for i in all_items]

    sales_data_queryset = Sale.objects.all().select_related('asset').order_by('sale_date')

    line_labels = []
    alis_maliyetleri = []
    endeksli_maliyetler = []
    satislar = []
    net_satislar = []
    final_sales_list = []

    system_latest_index = latest_index

    cum_alis = cum_endeksli = cum_satis = cum_net = Decimal('0.00')

    def clean_decimal(v, fallback="0.00"):
        if v is None or v == "":
            return Decimal(fallback)
        try:
            return Decimal(str(v).strip().replace('\xa0', '').replace(',', '.'))
        except Exception:
            return Decimal(fallback)

    for s in sales_data_queryset:

        try:
            qty = Decimal(str(s.quantity or 0))
            sale_price = Decimal(str(s.sale_price_foreign or 0))
            commission = Decimal(str(s.sale_commission_foreign or 0))
            fx = Decimal(str(s.sale_exchange_rate or 1))

            sale_tl = ((qty * sale_price) - commission) * fx

            tx = s.purchase_hash

            buy_price = sale_price
            buy_commission = Decimal('0.00')
            buy_fx = fx
            buy_index = Decimal('1.00')

            if tx and '|' in str(tx):
                p = str(tx).split('|')
                if len(p) >= 5:
                    buy_price = clean_decimal(p[1])
                    buy_commission = clean_decimal(p[2])
                    buy_fx = clean_decimal(p[3], "1.00")
                    buy_index = clean_decimal(p[4], "1.00")

            cost = ((qty * buy_price) + buy_commission) * buy_fx

            multiplier = system_latest_index / buy_index if buy_index > 0 else Decimal('1.00')
            multiplier = multiplier if multiplier >= Decimal('1.10') else Decimal('1.00')

            indexed_cost = cost * multiplier
            net = sale_tl - indexed_cost

            cum_alis += cost
            cum_endeksli += indexed_cost
            cum_satis += sale_tl
            cum_net += net

            line_labels.append(s.sale_date.strftime('%d-%m-%Y') if s.sale_date else "-")

            alis_maliyetleri.append(float(cum_alis))
            endeksli_maliyetler.append(float(cum_endeksli))
            satislar.append(float(cum_satis))
            net_satislar.append(float(cum_net))

            final_sales_list.append({
                'db_date': s.sale_date,
                'db_asset_symbol': s.asset.symbol,
                'db_quantity': float(qty),
                'calc_purchase_value': float(cost),
                'calc_indexed_purchase': float(indexed_cost),
                'calc_sale_value': float(sale_tl),
                'calc_net_profit': float(net),
            })

        except Exception:
            logger.exception("Sale processing error")

    def safe_fx(symbol):
        try:
            return get_live_data_cached(symbol, 'FOREX', symbol)[1]
        except:
            return Decimal("1.00")

    usd_kur = safe_fx('USD')
    eur_kur = safe_fx('EUR')
    
    def clean_nan(value):

        if isinstance(value, Decimal):
            if value.is_nan() or value.is_infinite():
                return Decimal('0.00')
        return value

    total_kalkan = clean_nan(total_kalkan_tl)
    total_kar_zarar = clean_nan(total_kar_zarar)
    total_reel_getiri = clean_nan(total_reel_getiri)
    total_maliyet = clean_nan(total_maliyet)
    total_reel_maliyet = clean_nan(total_reel_maliyet)
    total_portfoy_degeri = clean_nan(total_portfoy_degeri)
   
    return render(request, 'dashboard.html', {
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
    })

def export_sales_csv(request):

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="vergi_beyan.csv"'
    response.write(codecs.BOM_UTF8)

    writer = csv.writer(response, delimiter=';')

    writer.writerow([
        'No', 'Hash', 'Tarih', 'Hisse',
        'Lot', 'Fiyat', 'Komisyon',
        'Para Birimi', 'TCMB Kur', 'Yİ-ÜFE'
    ])

    sales = Sale.objects.all().select_related('asset').order_by('sale_date')

    include_bist = False
    include_cr = False

    for i, s in enumerate(sales, start=1):

        if (
            (not include_bist and s.asset.asset_type == "BIST") or
            (not include_cr and s.asset.asset_type == "CRYPTO")
        ):
            continue

        writer.writerow([
            i,
            s.purchase_hash,
            s.sale_date.strftime('%d/%m/%Y'),
            s.asset.symbol,
            s.quantity,
            s.sale_price_foreign,
            s.sale_commission_foreign,
            getattr(s.asset, "currency", "TRY"),
            s.sale_exchange_rate,
            s.sale_index
        ])

    return response
