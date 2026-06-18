from decimal import Decimal

from django.contrib import admin

from .models import Asset, IndicativeExchangeRate, InflationIndex, Sale, Transaction
from .utils import execute_fifo_sale

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'asset_type')
    list_filter = ('asset_type',)
    search_fields = ('symbol', 'name')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('asset', 'date', 'transaction_type', 'amount', 'price_foreign', 'display_remaining')
    list_filter = ('transaction_type', 'asset')
    date_hierarchy = 'date'
    exclude = ('remaining_quantity',)
    
    def save_model(self, request, obj, form, change):
            from decimal import Decimal

            if not change and obj.transaction_type == 'SELL':
                if obj.asset.asset_type == 'BIST':
                    obj.exchange_rate = Decimal('1.0000')
                else:
                    if obj.exchange_rate == Decimal('1.0000') or obj.exchange_rate == 0 or obj.exchange_rate is None:
                        obj.exchange_rate = obj.get_suggested_rate(obj.asset, obj.date)

                try:
                    from .utils import execute_fifo_sale
                    execute_fifo_sale(
                        asset=obj.asset,
                        sell_qty=obj.amount,
                        sell_px_foreign=obj.price_foreign,
                        s_date=obj.date,
                        s_kur=obj.exchange_rate,
                        s_comm=obj.commission_foreign
                    )
                    super().save_model(request, obj, form, change)
                except Exception as e:
                    from django.contrib import messages
                    messages.error(request, f"Hata: {str(e)}")
            else:
                if obj.asset.asset_type == 'BIST':
                    obj.exchange_rate = Decimal('1.0000')
                else:
                    if obj.exchange_rate == Decimal('1.0000') or obj.exchange_rate == 0 or obj.exchange_rate is None:
                        obj.exchange_rate = obj.get_suggested_rate(obj.asset, obj.date)
                super().save_model(request, obj, form, change)

    @admin.display(description='Kalan Stok')
    def display_remaining(self, obj):
        if obj.transaction_type == 'SELL':
            return "-"
        return obj.remaining_quantity

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('asset', 'sale_date', 'quantity', 'sale_price_foreign', 'sale_exchange_rate')

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(InflationIndex)
class InflationIndexAdmin(admin.ModelAdmin):
    list_display = ('year', 'month', 'value')
    list_filter = ('year',)
    ordering = ('-year', '-month')

@admin.register(IndicativeExchangeRate)
class IndicativeExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('date', 'usd_forex_buying', 'eur_forex_buying')
    list_filter = ('date',)
    
