from django.db import models
from dateutil.relativedelta import relativedelta
from decimal import Decimal

class Asset(models.Model):
	
    class Meta:
        verbose_name = "varlık"
        verbose_name_plural = "Varlıklar"
		
    ASSET_TYPES = [
        ('BIST', 'Borsa İstanbul (TL)'),
        ('US', 'Amerikan Borsası (USD)'),
        ('EU', 'Avrupa Borsası (EUR)'),
        ('CRYPTO', 'Kripto Para (USD)'),
    ]
    name = models.CharField(max_length=100, verbose_name="Varlık Adı")
    symbol = models.CharField(max_length=20, unique=True, verbose_name="Sembol")
    asset_type = models.CharField(max_length=10, choices=ASSET_TYPES, verbose_name="Varlık Türü")

    def __str__(self):
        return f"{self.symbol} - {self.name}"

class Transaction(models.Model):

    class Meta:
        verbose_name = "transaksiyon"
        verbose_name_plural = "Transaksiyonlar"
	
    TRANSACTION_TYPES = [
        ('BUY', 'Alış'),
        ('SELL', 'Satış'),
    ]
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, verbose_name="Varlık")
    date = models.DateField(verbose_name="İşlem Tarihi")
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES, verbose_name="İşlem Türü")

    # Miktar ve Fiyat
    amount = models.DecimalField(max_digits=18, decimal_places=8, verbose_name="Adet")
    price_foreign = models.DecimalField(max_digits=18, decimal_places=2, verbose_name="Birim Fiyat (Döviz/TL)")
    commission_foreign = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Komisyon (Döviz/TL)")

    # Kurlar ve Endeksler (Vergi ve Analiz İçin)
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True, default=1.0, verbose_name="Kur")
    yi_ufe_index = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, verbose_name="Yİ-ÜFE")

    # FIFO Stok Takibi
    remaining_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        default=0,
        verbose_name="Kalan Stok"
    )
    
    @staticmethod
    def get_suggested_rate(asset, date):
        from .models import IndicativeExchangeRate
        currency_type = 'EUR' if asset.asset_type == 'EU' else 'USD'
        rate_obj = IndicativeExchangeRate.objects.filter(date__lte=date).order_by('-date').first()
        if rate_obj:
            return rate_obj.usd_forex_buying if currency_type == 'USD' else rate_obj.eur_forex_buying
        return Decimal('1.0000')

    def save(self, *args, **kwargs):
            # 1. OTOMATİK KUR ÇEKME MANTIĞI ---
            if self.asset.asset_type == 'BIST':
                # TL ise varsayılan 1.0000 değerini koru/zorla
                self.exchange_rate = Decimal('1.0000')
            else:
                # Döviz ise ve kullanıcı dokunmayıp kur 1.0000 ise, 0 ise veya boşsa otomatik çek!
                if self.exchange_rate == Decimal('1.0000') or self.exchange_rate == 0 or self.exchange_rate is None:
                    # Tüm kur bulma işini tek satırda temizce çözer, özel kurları ezmez!
                    self.exchange_rate = self.get_suggested_rate(self.asset, self.date)        

            # 2. YI-ÜFE ENDEKSLEME (M-1) ---
            if self.yi_ufe_index is None:
                from dateutil.relativedelta import relativedelta
                m1_date = self.date - relativedelta(months=1)
                idx_obj = InflationIndex.objects.filter(year=m1_date.year, month=m1_date.month).first()
                if idx_obj:
                    self.yi_ufe_index = idx_obj.value

            # 3. STOK YÖNETMİ (BUY/SELL) ---
            if not self.pk and self.transaction_type == 'BUY':
                self.remaining_quantity = self.amount
            
            if self.transaction_type == 'SELL':
                self.remaining_quantity = 0

            # 4. ANA KAYIT ---
            super().save(*args, **kwargs)

    @property
    def symbol(self):
        return self.asset.symbol

    @property
    def generate_hash(self):
        """Excel'in beklediği mühürlü veri paketi"""
        # Format: Tarih|Fiyat|Komisyon|Kur|Endeks
        return f"{self.date.strftime('%d/%m/%Y')}|{self.price_foreign}|{self.commission_foreign}|{self.exchange_rate}|{self.yi_ufe_index}"

class Sale(models.Model):
	
    """Excel Çıktısı ve Beyan Arşivi"""
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    sale_date = models.DateField(verbose_name="Satış Tarihi")
    quantity = models.DecimalField(max_digits=18, decimal_places=8, verbose_name="Satılan Adet")

    # Satış Verileri (Dondurulmuş)
    sale_price_foreign = models.DecimalField(max_digits=18, decimal_places=4, verbose_name="Satış Fiyatı")
    sale_commission_foreign = models.DecimalField(max_digits=18, decimal_places=4, verbose_name="Satış Komisyonu")
    sale_exchange_rate = models.DecimalField(max_digits=18, decimal_places=4, verbose_name="Satış Kuru")
    sale_index = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Excel'e pas atılacak "Sihirli" hücre
    purchase_hash = models.TextField(verbose_name="Alış İşlem Kodu (Hash)")
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'asset',
                    'sale_date',
                    'quantity',
                    'purchase_hash'
                ],
                name='unique_fifo_sale'
            )
        ]

        verbose_name = "satış"
        verbose_name_plural = "Satışlar"

    def __str__(self):
        return f"{self.sale_date} - {self.asset.symbol} ({self.quantity} Adet)"

class InflationIndex(models.Model):
    year = models.IntegerField(verbose_name="Yıl")
    month = models.IntegerField(verbose_name="Ay")
    value = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, verbose_name="Değer")

    class Meta:
        unique_together = ('year', 'month')
        verbose_name = "endeks"
        verbose_name_plural = "Yurtiçi Üretici Endeksi"

    def __str__(self):
        return f"{self.year}/{self.month} - {self.value}"

class IndicativeExchangeRate(models.Model):
    date = models.DateField(verbose_name="Tarih", unique=True)
    usd_forex_buying = models.DecimalField(max_digits=18, decimal_places=4, verbose_name="USD/TRY")
    eur_forex_buying = models.DecimalField(max_digits=18, decimal_places=4, verbose_name="EUR/TRY")
    
    class Meta:
        verbose_name = "Kur"
        verbose_name_plural = "TCMB Forex Alış Kurları"
        ordering = ['-date']

    def __str__(self):
        return f"{self.date.strftime('%d.%m.%Y')} tarihinde USD : {self.usd_forex_buying} TL - EUR : {self.eur_forex_buying} TL'dir."
