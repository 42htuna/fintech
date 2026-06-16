import requests
from datetime import datetime
from .models import InflationIndex
from decimal import Decimal

def fetch_yi_ufe_data(api_key):
    series_code = "TP.YI_UFE.GENEL" 
    start_date = "01-01-2025"
    end_date = datetime.now().strftime("%d-%m-%Y")
    
    url = f"https://evds2.tcmb.gov.tr/service/evds/series={series_code}&startDate={start_date}&endDate={end_date}&type=json&key={api_key}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if "html" in response.headers.get('Content-Type', '').lower():
            print("❌ HATA: Sunucu JSON yerine HTML döndü. API anahtarını kontrol et veya IP kısıtlamasını kaldır.")
            return False
            
        data = response.json()
        
        if 'items' in data:
            count = 0
            for item in data['items']:\
                pass
            return True
            
    except Exception as e:
        print(f"❌ API Hatası oluştu: {e}")
        return False
        
    return False
