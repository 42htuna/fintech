from decimal import Decimal
import json
from pathlib import Path

from django.core.management.base import BaseCommand
import pandas as pd

from investments.models import IndicativeExchangeRate
from investments.utils import excel_den_kur_yukle

class Command(BaseCommand):
    help = 'Excel veya JSON dosyasından kur verilerini akıllıca yükler.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='tcmb_kur_verileri.xlsx',
            help='Yüklenecek kaynak dosya (Excel veya JSON)'
        )

    def handle(self, *args, **options):
        girilen_dosya = Path(options['file'])
        self.stdout.write(f"DEBUG: İşlenen Dosya: {girilen_dosya.absolute()}")
        self.stdout.write(f"DEBUG: Dosya Mevcut mu?: {girilen_dosya.exists()}")    
        
        if girilen_dosya.suffix == '.xlsx':
            dosya_excel = girilen_dosya
            dosya_json = girilen_dosya.with_suffix('.json')
        elif girilen_dosya.suffix == '.json':
            dosya_json = girilen_dosya
            dosya_excel = girilen_dosya.with_suffix('.xlsx')
        else:
            self.stdout.write(self.style.ERROR("💥 Hata: Yalnızca .xlsx veya .json desteklenmektedir!"))
            return

        if not dosya_excel.exists():
            self.stdout.write(self.style.WARNING(f"⚠️ Ana Excel dosyası ({dosya_excel}) bulunamadı."))

            if dosya_json.exists():
                self.stdout.write(self.style.SUCCESS(f"📂 JSON bulundu! Veriler {dosya_json} içinden okunuyor..."))
                try:
                    with open(dosya_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    if not data:
                        self.stdout.write(self.style.WARNING("⚠️ JSON dosyası boş, yüklenecek veri yok."))
                        return

                    mevcut_tarihler = set(IndicativeExchangeRate.objects.values_list('date', flat=True))
                    kayitlar = []

                    for item in data:
                        tarih_raw = item.get('Tarih')
                        usd_raw = item.get('USD/TRY')
                        eur_raw = item.get('EUR/TRY')

                        if not tarih_raw or pd.isna(usd_raw) or pd.isna(eur_raw):
                            continue

                        target_date = pd.to_datetime(tarih_raw, dayfirst=True).date()

                        if target_date in mevcut_tarihler:
                            continue

                        kayitlar.append(
                            IndicativeExchangeRate(
                                date=target_date,
                                usd_forex_buying=Decimal(str(usd_raw).replace(',', '.')),
                                eur_forex_buying=Decimal(str(eur_raw).replace(',', '.'))
                            )
                        )

                    if kayitlar:
                        IndicativeExchangeRate.objects.bulk_create(kayitlar)
                        self.stdout.write(self.style.SUCCESS(f"✅ {len(kayitlar)} adet yeni kur verisi JSON'dan başarıyla yüklendi."))
                    else:
                        self.stdout.write(self.style.WARNING("ℹ️ Yüklenecek kur verisi bulunamadı, veritabanı zaten güncel!"))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"💥 JSON okunurken hata: {e}"))
                return
            
            else:
                with open(dosya_json, "w", encoding="utf-8") as f:
                    json.dump([], f)
                self.stdout.write(self.style.ERROR(f"💥 Hata: Ne Excel ne de JSON dosyası bulundu!"))
                self.stdout.write(self.style.WARNING(f"⚠️ {dosya_json} adında boş bir şablon oluşturuldu."))
                return

        elif not dosya_json.exists():
            self.stdout.write(self.style.WARNING(f"⚠️ {dosya_json} bulunamadı. Önce Excel'den yedek JSON üretiliyor..."))
            try:
                df = pd.read_excel(dosya_excel)
                df.columns = df.columns.str.strip()
                
                if 'Tarih' in df.columns:
                    df['Tarih'] = df['Tarih'].astype(str)

                df_json_data = df.to_dict(orient='records')
                
                with open(dosya_json, "w", encoding="utf-8") as f:
                    json.dump(df_json_data, f, ensure_ascii=False, indent=4)
                self.stdout.write(self.style.SUCCESS(f"✅ {dosya_json} başarıyla üretildi."))
                
                self.stdout.write("📂 Orijinal Excel fonksiyonu çalıştırılıyor...")
                excel_den_kur_yukle(str(dosya_excel))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"💥 Excel işlenirken hata oluştu: {e}"))
                return

        else:
            self.stdout.write(self.style.SUCCESS(f"🟢 Güncel Excel dosyası ({dosya_excel}) bulundu."))
            try:
                excel_den_kur_yukle(str(dosya_excel))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"💥 Excel yüklemesi sırasında hata: {e}"))
