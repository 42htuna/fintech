from django.core.management.base import BaseCommand

from investments.utils import fill_missing_inflation_values

class Command(BaseCommand):
    help = 'NULL olan yi_ufe_index alanlarını M-1 kuralına göre doldurur.'

    def handle(self, *args, **options):

        updated = fill_missing_inflation_values()

        self.stdout.write(self.style.SUCCESS(
            f"İşlem tamamlandı: {updated} güncellendi."
        ))
