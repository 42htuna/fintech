from django.contrib import admin
from django.urls import path
from investments import views

urlpatterns = [
    # Admin Paneli
    path('admin/', admin.site.urls),
    
    # Ana Sayfa (Yatırım Komuta Merkezi)
    path('', views.portfolio_dashboard, name='dashboard'),
    
    # Excel Çıktısı (Hash Mühürlü CSV)
    path('export-sales/', views.export_sales_csv, name='export_sales'),
]
