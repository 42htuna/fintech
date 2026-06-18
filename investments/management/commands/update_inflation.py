from django.conf import settings

from django.core.management.base import BaseCommand

from investments.crawler import fetch_yi_ufe_data

class Command(BaseCommand):
    help = 'TCMB EVDS üzerinden Yİ-ÜFE verilerini günceller.'

    def handle(self, *args, **options):
        
        if not settings.EVDS_KEY:
            self.stdout.write(
                self.style.ERROR("💥 HATA: EVDS_API_KEY tanımlı değil!")
            )
            return        

        success = fetch_yi_ufe_data(settings.EVDS_KEY)
        
        if success:
            self.stdout.write(
                self.stdout.write(self.style.SUCCESS('✅ Enflasyon verileri TCMB EVDS üzerinden başarıyla tazelendi.'))
            )
        else:
            self.stdout.write(
                self.style.ERROR("💥 HATA: Enflasyon verileri güncellenemedi! Yukarıdaki log detaylarını inceleyin.")
            )
