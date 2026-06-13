from .models import InflationIndex
from decimal import Decimal
import yfinance as yf

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

    def fetch_with_fallback(sym, asset_type):
        suffixes = ["L", "DE", "AS", "PA", "MI"] if asset_type in ["EU", "US"] else []
        
        for s in [sym] + [f"{sym}.{suf}" for suf in suffixes]:
            hist = yf.Ticker(s).history(period="5d", interval="1d")
            if not hist.empty:
                return yf.Ticker(s), hist, s
        return None, None, None

    ticker, hist, ticker_sym = fetch_with_fallback(ticker_sym, asset_type)
    
    if hist is None or hist["Close"].empty:
        raise ValueError(f"{symbol} için canlı veri bulunamadı.")

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
