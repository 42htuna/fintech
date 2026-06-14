from django.contrib import admin
from django.urls import path
from investments import views
from django.conf import settings
from django.urls import path, re_path
from django.views.generic.base import RedirectView

urlpatterns = [
    # Admin Paneli
    path('admin/', admin.site.urls),
    
    # Ana Sayfa (Yatırım Komuta Merkezi)
    path('', views.portfolio_dashboard, name='dashboard'),
    
    # Excel Çıktısı (Hash Mühürlü CSV)
    path('export-sales/', views.export_sales_csv, name='export_sales'),
]

urlpatterns += [
        
    re_path(r'^(?P<filename>.+\.(?:png|jpg|jpeg|gif|ico|svg))$', 
           lambda request, filename: RedirectView.as_view(url=settings.STATIC_URL + filename)(request)),
]
