from decimal import Decimal
from .models import InflationIndex
import yfinance as yf
from decimal import Decimal

def calculate_real_cost(transaction):
    """
    İşlemin yapıldığı aydaki Yİ-ÜFE ile en güncel Yİ-ÜFE'yi
    kıyaslayarak enflasyondan arındırılmış maliyeti hesaplar.
    """
    # 1. Alış tarihindeki endeksi bul
    buy_index = InflationIndex.objects.filter(
        year=transaction.date.year,
        month=transaction.date.month
    ).first()

    # 2. En güncel (son açıklanan) endeksi bul
    latest_index = InflationIndex.objects.order_by('-year', '-month').first()

    if not buy_index or not latest_index:
        # Veri eksikse katsayıyı 1 kabul et (hesaplama yapma)
        return transaction.total_tl

    # 3. Katsayıyı Hesapla (Örn: 1.3748)
    multiplier = latest_index.value / buy_index.value

    # 4. Reel Maliyeti Hesapla
    real_cost = transaction.total_tl * multiplier
    return real_cost.quantize(Decimal('0.01'))

def get_live_data(symbol, asset_type):
    try:
        if asset_type == 'BIST':
            ticker_sym = f"{symbol}.IS"
        elif asset_type == 'CRYPTO':
            ticker_sym = f"{symbol}-USD"
        elif asset_type == 'FOREX':
            ticker_sym = f"{symbol}TRY=X"
        elif asset_type == 'EU':
            ticker_sym = symbol if "." in symbol else f"{symbol}.AS"
        else:
            ticker_sym = symbol

        ticker = yf.Ticker(ticker_sym)
        hist = ticker.history(period="1d")
        
        if hist.empty and asset_type == 'EU' and ticker_sym.endswith(".AS"):
            print(f"Uyarı: {ticker_sym} boş döndü, ASML.DE deneniyor...")
            ticker = yf.Ticker(f"{symbol}.DE")
            hist = ticker.history(period="1d")        

        if hist.empty:
            print(f"UYARI: {ticker_sym} sembolü için veri bulunamadı!")
            return Decimal('0.00'), Decimal('1.00')

        price = Decimal(str(hist['Close'].iloc[-1]))

        # Kur çekme mantığı
        if asset_type == 'BIST':
            exchange_rate = Decimal('1.00')
        elif asset_type == 'FOREX':
            # YENİ: Döviz tipinde exchange_rate doğrudan fiyatın kendisine eşittir
            exchange_rate = price
        else:
            # USD veya EUR kuru (Sembol bazlı basit mantık)
            currency = "USDTRY=X" if asset_type in ['US', 'CRYPTO'] else "EURTRY=X"
            rate_hist = yf.Ticker(currency).history(period="1d")
            exchange_rate = Decimal(str(rate_hist['Close'].iloc[-1]))

        return price, exchange_rate
    except:
        return Decimal('0.00'), Decimal('1.00')
