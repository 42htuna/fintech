# 1. Grup: Standart Kütüphaneler
from decimal import Decimal
import json
from pathlib import Path

# 2. Grup: Üçüncü Parti Kütüphaneler
from django.core.management.base import BaseCommand
import pandas as pd

# 3. Grup: Yerel Uygulama Modülleri
from investments.models import InflationIndex, IndicativeExchangeRate
from investments.utils import excel_den_enflasyon_yukle, excel_den_kur_yukle

class Command(BaseCommand):
    help = 'Excel veya JSON kaynaklarından Kur veya Enflasyon (Yİ-ÜFE) verilerini akıllıca yükler.'

    def add_arguments(self, parser):
        # Hangi verinin yükleneceğini seçmek için "mutually exclusive" (birbiriyle çelişen/seçimli) grup oluşturuyoruz.
        # Bu sayede kullanıcı ya --endeks ya da --kur girmek zorunda kalacak, ikisini aynı anda giremeyecek.
        grup = parser.add_mutually_exclusive_group(required=True)
        grup.add_argument(
            '--endeks',
            action='store_true',
            help='Yİ-ÜFE Enflasyon endeks verilerini yükler.'
        )
        grup.add_argument(
            '--kur',
            action='store_true',
            help='TCMB döviz kuru verilerini yükler.'
        )

        # İsteğe bağlı olarak özel dosya yolu belirtmek istersen diye bu argümanı ortak yapıyoruz
        parser.add_argument(
            '--file',
            type=str,
            default=None,
            help='Varsayılan dosya yerine özel bir dosya yolu belirtmek için kullanılır.'
        )

    def handle(self, *args, **options):
        # -----------------------------------------------------------------
        # MOD SEÇİMİ VE VARSAYILAN DOSYA AYARLARI
        # -----------------------------------------------------------------     
        if options['endeks']:
            mod = "ENFLASYON"
            varsayilan_dosya = "tcmb_enflasyon_verileri.xlsx"
        else:
            mod = "KUR"
            varsayilan_dosya = "tcmb_kur_verileri.xlsx"

        # Kullanıcı özel dosya girdiyse onu, girmediyse modun varsayılan dosyasını alıyoruz
        girilen_dosya = Path(options['file']) if options['file'] else Path(varsayilan_dosya)

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

        self.stdout.write(self.style.SUCCESS(f"🚀 Mod: {mod} | Kaynak aranıyor..."))

        # =================================================================
        # BÖLÜM A: ENFLASYON (ENDEKS) YÜKLEME MANTIĞI
        # =================================================================
        if mod == "ENFLASYON":
            # 1. Senaryo: Excel yok, JSON var (Yan Yol)
            if not dosya_excel.exists():
                self.stdout.write(self.style.WARNING(f"⚠️ {dosya_excel} bulunamadı."))
                if dosya_json.exists():
                    self.stdout.write(self.style.SUCCESS(f"📂 JSON bulundu! Direkt {dosya_json} işleniyor..."))
                    try:
                        with open(dosya_json, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        basarili = 0
                        for item in data:
                            year = item.get('Yil')
                            month = item.get('Ay')
                            val = item.get('Yİ_UFE_Endeks')
                            if year and month and val is not None:
                                InflationIndex.objects.update_or_create(
                                    year=int(year), month=int(month),
                                    defaults={'value': Decimal(str(val))}
                                )
                                basarili += 1
                        self.stdout.write(self.style.SUCCESS(f'✅ {basarili} adet endeks verisi JSON\'dan yüklendi!'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"💥 JSON hatası: {e}"))
                    return
                else:
                    with open(dosya_json, "w", encoding="utf-8") as f: json.dump([], f)
                    self.stdout.write(self.style.ERROR(f"💥 Hata: Kaynak bulunamadı, boş {dosya_json} oluşturuldu."))
                    return

            # 2. Senaryo: Excel var, JSON yoksa (JSON Üret ve Orijinal Utils'i Tetikle)
            elif not dosya_json.exists():
                self.stdout.write(self.style.WARNING(f"⚠️ {dosya_json} bulunamadı. Önce Excel'den yedek JSON üretiliyor..."))
                try:
                    df = pd.read_excel(dosya_excel, usecols=['Tarih', 'Yİ_UFE_Endeks'])
                    df.columns = df.columns.str.strip()
                    df['Tarih_Dt'] = pd.to_datetime(df['Tarih'])
                    df['Yil'] = df['Tarih_Dt'].dt.year
                    df['Ay'] = df['Tarih_Dt'].dt.month
                    df_json_data = df[['Yil', 'Ay', 'Yİ_UFE_Endeks']].to_dict(orient='records')
                    with open(dosya_json, "w", encoding="utf-8") as f:
                        json.dump(df_json_data, f, ensure_ascii=False, indent=4)
                    self.stdout.write(self.style.SUCCESS(f'✅ {dosya_json} başarıyla oluşturuldu.'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"💥 Excel'den JSON üretilirken hata: {e}"))
                    return
            
            # 3. Senaryo: Doğrudan Orijinal Enflasyon Utils Fonksiyonu
            try:
                excel_den_enflasyon_yukle(str(dosya_excel))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"💥 Excel yükleme hatası: {e}"))

        # =================================================================
        # BÖLÜM B: KUR YÜKLEME MANTIĞI
        # =================================================================
        elif mod == "KUR":
            # 1. Senaryo: Excel yok, JSON var (Yan Yol)
            if not dosya_excel.exists():
                self.stdout.write(self.style.WARNING(f"⚠️ {dosya_excel} bulunamadı."))
                if dosya_json.exists():
                    self.stdout.write(self.style.SUCCESS(f"📂 JSON bulundu! Direkt {dosya_json} işleniyor..."))
                    try:
                        with open(dosya_json, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        mevcut_tarihler = set(IndicativeExchangeRate.objects.values_list('date', flat=True))
                        kayitlar = []
                        for item in data:
                            tarih_raw, usd_raw, eur_raw = item.get('Tarih'), item.get('USD/TRY'), item.get('EUR/TRY')
                            if not tarih_raw or pd.isna(usd_raw) or pd.isna(eur_raw): continue
                            target_date = pd.to_datetime(tarih_raw, dayfirst=True).date()
                            if target_date in mevcut_tarihler: continue
                            kayitlar.append(
                                IndicativeExchangeRate(
                                    date=target_date,
                                    usd_forex_buying=Decimal(str(usd_raw).replace(',', '.')),
                                    eur_forex_buying=Decimal(str(eur_raw).replace(',', '.'))
                                )
                            )
                        if kayitlar:
                            IndicativeExchangeRate.objects.bulk_create(kayitlar)
                            self.stdout.write(self.style.SUCCESS(f"✅ {len(kayitlar)} adet kur verisi JSON'dan bulk_create ile yüklendi."))
                        else:
                            self.stdout.write(self.style.WARNING("ℹ️ Yüklenecek yeni kur verisi bulunamadı."))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"💥 JSON hatası: {e}"))
                    return
                else:
                    with open(dosya_json, "w", encoding="utf-8") as f: json.dump([], f)
                    self.stdout.write(self.style.ERROR(f"💥 Hata: Kaynak bulunamadı, boş {dosya_json} oluşturuldu."))
                    return

            # 2. Senaryo: Excel var, JSON yoksa (JSON Üret ve Orijinal Utils'i Tetikle)
            elif not dosya_json.exists():
                self.stdout.write(self.style.WARNING(f"⚠️ {dosya_json} bulunamadı. Önce Excel'den yedek JSON üretiliyor..."))
                try:
                    df = pd.read_excel(dosya_excel)
                    df.columns = df.columns.str.strip()
                    if 'Tarih' in df.columns: df['Tarih'] = df['Tarih'].astype(str)
                    df_json_data = df.to_dict(orient='records')
                    with open(dosya_json, "w", encoding="utf-8") as f:
                        json.dump(df_json_data, f, ensure_ascii=False, indent=4)
                    self.stdout.write(self.style.SUCCESS(f'✅ {dosya_json} başarıyla oluşturuldu.'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"💥 Excel'den JSON üretilirken hata: {e}"))
                    return

            # 3. Senaryo: Doğrudan Orijinal Kur Utils Fonksiyonu
            try:
                excel_den_kur_yukle(str(dosya_excel))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"💥 Excel yükleme hatası: {e}"))
