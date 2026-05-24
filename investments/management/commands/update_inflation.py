from django.core.management.base import BaseCommand
from investments.crawler import fetch_yi_ufe_data

class Command(BaseCommand):
    help = 'TCMB EVDS üzerinden Yİ-ÜFE verilerini günceller'

    def handle(self, *args, **options):
        # API fonksiyonunu çalıştır ve durumunu bir değişkene eşitle
        success = fetch_yi_ufe_data("YOUR_API_KEY")
        
        if success:
            # Sadece fonksiyon True döndüyse başarı mesajı bas
            self.stdout.write(self.style.SUCCESS('✅ Enflasyon verileri TCMB EVDS üzerinden başarıyla tazelendi!'))
        else:
            # Fonksiyon hata verip False döndüyse kırmızı alarm ver
            self.stdout.write(
                self.style.ERROR('💥 HATA: Enflasyon verileri güncellenemedi! Yukarıdaki log detaylarını inceleyin.')
            )
