from decimal import Decimal

from django.contrib import admin, messages

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
        if obj.asset.asset_type == 'BIST':
            obj.exchange_rate = Decimal('1.0000')
        else:
            if obj.exchange_rate in [Decimal('1.0000'), Decimal('0'), None]:
                obj.exchange_rate = obj.get_suggested_rate(obj.asset, obj.date)

        super().save_model(request, obj, form, change)

        if not change and obj.transaction_type == 'SELL':
            try:
                execute_fifo_sale(
                    sell_transaction=obj,
                    asset=obj.asset,
                    sell_qty=obj.amount,
                    sell_px_foreign=obj.price_foreign,
                    s_date=obj.date,
                    s_kur=obj.exchange_rate,
                    s_comm=obj.commission_foreign
                )
            except Exception as e:
                obj.delete()
                messages.error(request, f"Hata: {str(e)} - Satış işlemi iptal edildi.")

    @admin.display(description='Kalan Stok')
    def display_remaining(self, obj):
        if obj.transaction_type == 'SELL':
            return "-"
        return obj.remaining_quantity

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('asset', 'sale_date', 'quantity', 'sale_price_foreign', 'sale_exchange_rate')
    list_filter = ('asset', 'sale_date',)
    
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
       
    def delete_model(self, request, obj):
        if obj.transaction:
            obj.transaction.delete()
        else:
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        transaction_ids = queryset.values_list('transaction_id', flat=True).exclude(transaction_id__isnull=True)
        Transaction.objects.filter(id__in=transaction_ids).delete()
        queryset.filter(transaction_id__isnull=True).delete()        

    actions = ['force_delete_action']
    
    @admin.action(description="Seçili satışları ZORLA SİL")
    def force_delete_action(self, request, queryset):
        count = queryset.count()
        transaction_ids = queryset.values_list('transaction_id', flat=True).exclude(transaction_id__isnull=True)
        Transaction.objects.filter(id__in=transaction_ids).delete()
        queryset.filter(transaction_id__isnull=True).delete()
        self.message_user(request, f"{count} adet satış kaydı ve bunlara bağlı ana işlemler mühürlü olmasına rağmen zorla silindi.", messages.WARNING)

@admin.register(InflationIndex)
class InflationIndexAdmin(admin.ModelAdmin):
    list_display = ('year', 'month', 'value')
    list_filter = ('year',)
    ordering = ('-year', '-month')

@admin.register(IndicativeExchangeRate)
class IndicativeExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('date', 'usd_forex_buying', 'eur_forex_buying')
    list_filter = ('date',)
    
