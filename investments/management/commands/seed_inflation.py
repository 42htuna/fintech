from decimal import Decimal

from django.core.management.base import BaseCommand

from investments.models import InflationIndex

class Command(BaseCommand):
    help = 'Yİ-ÜFE verilerini manuel olarak yükler.'

    def handle(self, *args, **options):
        data = [
            (2025, 1, '3861.33'),
            (2025, 2, '3943.01'),
            (2025, 3, '4017.30'),
            (2025, 4, '4128.19'),
            (2025, 5, '4230.69'),
            (2025, 6, '4334.94'),
            (2025, 7, '4409.73'),
            (2025, 8, '4518.89'),
            (2025, 9, '4632.89'),
            (2025, 10, '4708.20'),
            (2025, 11, '4747.63'),
            (2025, 12, '4783.04'),
            (2026, 1, '4910.53'),
            (2026, 2, '5029.76'),
            (2026, 3, '5145.36'),
            (2026, 4, '5308.46'),
        ]

        for year, month, val in data:
            InflationIndex.objects.update_or_create(
                year=year, month=month,
                defaults={'value': Decimal(val)}
            )
        
        self.stdout.write(self.style.SUCCESS(f'✅ {len(data)} adet endeks verisi başarıyla yüklendi!'))
