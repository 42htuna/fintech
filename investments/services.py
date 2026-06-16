from decimal import Decimal, InvalidOperation
from django.core.cache import cache
from .models import InflationIndex
from datetime import datetime
import yfinance as yf
import requests

custom_session = requests.Session()
custom_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

EU_HINTS = {
    "ASML": "AS", 
    "ADYEN": "AS", 
    "SAP": "DE", 
    "SIE": "DE", 
    "BMW": "DE", 
    "VOW3": "DE", 
    "AIR": "PA", 
    "MC": "PA", 
    "OR": "PA", 
    "ENI": "MI", 
    "ISP": "MI",
    "VUAA": "L", 
    "MEUD": "MI"
}

SYMBOL_OVERRIDES = {
    'VUAA': 'VUAA.L',
    'MEUD': 'MEUD.MI',
    'ASML': 'ASML.AS',
}

def calculate_real_cost(transaction):
    buy_index = InflationIndex.objects.filter(year=transaction.date.year, month=transaction.date.month).first()
    latest_index = InflationIndex.objects.order_by('-year', '-month').first()

    if not buy_index or not latest_index or buy_index.value <= 0:
        return Decimal(str(transaction.total_tl or 0)).quantize(Decimal('0.01'))

    multiplier = latest_index.value / buy_index.value
    final_multiplier = multiplier if multiplier >= Decimal('1.10') else Decimal('1.00')
    
    real_cost = Decimal(str(transaction.total_tl or 0)) * final_multiplier
    return real_cost.quantize(Decimal('0.01'))

def get_live_data(symbol, asset_type, currency):
    if "." in symbol:
        ticker_sym = symbol
    elif symbol in SYMBOL_OVERRIDES:
        ticker_sym = SYMBOL_OVERRIDES[symbol]   
    elif asset_type == "EU":
        ticker_sym = f"{symbol}.{EU_HINTS.get(symbol, 'AS')}"     
    elif asset_type == 'BIST':
        ticker_sym = f"{symbol}.IS"
    elif asset_type == 'CRYPTO':
        ticker_sym = f"{symbol}-USD"
    elif asset_type == 'FOREX':
        ticker_sym = f"{symbol}TRY=X"
    else:
        ticker_sym = symbol

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"[{timestamp}] [DEBUG] Fetching: {symbol} -> Ticker: {ticker_sym} (Asset: {asset_type})")    
    
    try:
        ticker = yf.Ticker(ticker_sym)
        hist = ticker.history(period="1d")
        
        if hist.empty:
            return Decimal("0.00"), Decimal("1.0")
            
        price = Decimal(str(hist["Close"].iloc[-1]))

        if asset_type == "BIST":
            exchange_rate = Decimal("1.00")
        elif asset_type == "FOREX":
            exchange_rate = price
        else:
            fx_pair = "EURTRY=X" if currency == "EUR" else "USDTRY=X"
            fx_hist = yf.Ticker(fx_pair).history(period="1d")           
            exchange_rate = Decimal(str(fx_hist["Close"].iloc[-1])) if not fx_hist.empty else Decimal("1.00")
            
        return price, exchange_rate
    except Exception:
        return Decimal("0.00"), Decimal("1.0")

def get_live_data_cached(symbol, asset_type, currency):
    cache_key = f"live_data_{symbol}_{asset_type}_{currency}"
    data = cache.get(cache_key)
    
    if data is not None:
        try:
            if Decimal(str(data[0])) <= Decimal("0.00"):
                data = None
        except:
            data = None

    if data is None:
        price, exchange_rate = get_live_data(symbol, asset_type, currency)
        
        if price > Decimal("0.00"):
            data = (price, exchange_rate)
            
            cache_timeout = 60 if asset_type == 'CRYPTO' else (300 if asset_type == 'BIST' else 1800)
            cache.set(cache_key, data, cache_timeout)
        else:
            data = (price, exchange_rate)
            
    return data
