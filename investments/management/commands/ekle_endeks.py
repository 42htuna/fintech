# 1. Grup: Standart Kütüphaneler
from decimal import Decimal
import json
from pathlib import Path

# 2. Grup: Üçüncü Parti Kütüphaneler
from django.core.management.base import BaseCommand
import pandas as pd

# 3. Grup: Yerel Uygulama Modülleri
from investments.models import InflationIndex
from investments.utils import excel_den_enflasyon_yukle

class Command(BaseCommand):
    help = 'Yİ-ÜFE verilerini Excel veya JSON dosyasından akıllıca yükler.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='tcmb_enflasyon_verileri.xlsx',
            help='Yüklenecek kaynak dosya (Excel veya JSON)'
        )

    def handle(self, *args, **options):
        girilen_dosya = Path(options['file'])
        self.stdout.write(f"DEBUG: İşlenen Dosya: {girilen_dosya.absolute()}")
        self.stdout.write(f"DEBUG: Dosya Mevcut mu?: {girilen_dosya.exists()}")            
        
        # Uzantı senkronizasyonu
        if girilen_dosya.suffix == '.xlsx':
            dosya_excel = girilen_dosya
            dosya_json = girilen_dosya.with_suffix('.json')
        elif girilen_dosya.suffix == '.json':
            dosya_json = girilen_dosya
            dosya_excel = girilen_dosya.with_suffix('.xlsx')
        else:
            self.stdout.write(self.style.ERROR("💥 Hata: Yalnızca .xlsx veya .json desteklenmektedir!"))
            return

        # -----------------------------------------------------------------
        # 1. SENARYO: Excel dosyası YOKSA (Sadece JSON varsa - Yan Yol)
        # -----------------------------------------------------------------
        if not dosya_excel.exists():
            self.stdout.write(self.style.WARNING(f"⚠️ Ana Excel dosyası ({dosya_excel}) bulunamadı."))

            if dosya_json.exists():
                self.stdout.write(self.style.SUCCESS(f"📂 JSON bulundu! Veriler direkt {dosya_json} üzerinden yükleniyor..."))
                try:
                    with open(dosya_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    if not data:
                        self.stdout.write(self.style.WARNING("⚠️ JSON dosyası boş, yüklenecek veri yok."))
                        return

                    basarili_kayit = 0
                    for item in data:
                        year = item.get('Yil')
                        month = item.get('Ay')
                        val = item.get('Yİ_UFE_Endeks')

                        if year and month and val is not None:
                            InflationIndex.objects.update_or_create(
                                year=int(year), 
                                month=int(month),
                                defaults={'value': Decimal(str(val))}
                            )
                            basarili_kayit += 1
                    
                    self.stdout.write(self.style.SUCCESS(f'✅ {basarili_kayit} adet endeks verisi JSON\'dan başarıyla yüklendi!'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"💥 JSON yan yolu çalışırken hata oluştu: {e}"))
                return
            else:
                with open(dosya_json, "w", encoding="utf-8") as f:
                    json.dump([], f)
                self.stdout.write(self.style.ERROR(f"💥 Hata: Ne Excel ne de JSON dosyası bulundu!"))
                self.stdout.write(self.style.WARNING(f"⚠️ {dosya_json} adında boş bir şablon oluşturuldu."))
                return

        # -----------------------------------------------------------------
        # 2. SENARYO: Excel VAR ama JSON YOKSA (Önce Excel'den JSON üret, sonra Orijinal Utils'i tetikle)
        # -----------------------------------------------------------------
        elif not dosya_json.exists():
            self.stdout.write(self.style.WARNING(f"⚠️ {dosya_json} bulunamadı. Önce Excel'den yedek JSON üretiliyor..."))
            try:
                df = pd.read_excel(dosya_excel, usecols=['Tarih', 'Yİ_UFE_Endeks'])
                df.columns = df.columns.str.strip()
                
                # Orijinal fonksiyonun tarih mantığına uyması için Yıl/Ay ayıklayıp JSON'a öyle yedekliyoruz
                df['Tarih_Dt'] = pd.to_datetime(df['Tarih'])
                df['Yil'] = df['Tarih_Dt'].dt.year
                df['Ay'] = df['Tarih_Dt'].dt.month
                
                df_json_data = df[['Yil', 'Ay', 'Yİ_UFE_Endeks']].to_dict(orient='records')
                
                with open(dosya_json, "w", encoding="utf-8") as f:
                    json.dump(df_json_data, f, ensure_ascii=False, indent=4)
                self.stdout.write(self.style.SUCCESS(f'✅ {dosya_json} başarıyla oluşturuldu.'))
                
                # JSON oluşturma bitti, şimdi senin orijinal utils fonksiyonunu tetikliyoruz
                self.stdout.write("📂 Orijinal Excel fonksiyonu çalıştırılıyor...")
                excel_den_enflasyon_yukle(str(dosya_excel))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"💥 Excel işlenirken hata oluştu: {e}"))
                return
        
        # -----------------------------------------------------------------
        # 3. SENARYO: Hem Excel Hem JSON VARSA (Doğrudan Orijinal Utils)
        # -----------------------------------------------------------------
        else:
            self.stdout.write(self.style.SUCCESS(f"🟢 Güncel Excel dosyası ({dosya_excel}) bulundu."))
            try:
                # Doğrudan mevcut utils fonksiyonunu tetikliyoruz
                excel_den_enflasyon_yukle(str(dosya_excel))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"💥 Excel yüklemesi sırasında hata: {e}"))
