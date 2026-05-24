import os
from django.core.management.base import BaseCommand
from investments.utils import excel_den_enflasyon_yukle

class Command(BaseCommand):
    help = 'Excel dosyasından enflasyon verilerini yükler.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='tcmb_enflasyon_verileri.xlsx'
        )

    def handle(self, *args, **options):

        file_path = options['file']

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'HATA: "{file_path}" bulunamadı.'))
            return

        try:
            self.stdout.write(self.style.SUCCESS(f'"{file_path}" okunuyor...'))

            excel_den_enflasyon_yukle(file_path)

            self.stdout.write(self.style.SUCCESS('İşlem başarıyla tamamlandı.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Hata: {e}'))
