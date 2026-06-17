import json
from django.core.management.base import BaseCommand
from investments.models import InflationIndex
from decimal import Decimal

class Command(BaseCommand):
    help = 'Yİ-ÜFE verilerini JSON dosyasından yükler.'

    def handle(self, *args, **options):
        file_path = 'tcmb_enflasyon_verileri.json' 
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    
        for year, month, val in data:
            InflationIndex.objects.update_or_create(
                year=year, 
                month=month,
                defaults={'value': Decimal(val)}
            )
        
        self.stdout.write(self.style.SUCCESS(f'✅ {len(data)} adet endeks verisi başarıyla yüklendi!'))
