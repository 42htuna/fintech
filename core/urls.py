# 1. Grup: Standart kütüphaneler

# 2. Grup: Üçüncü parti (Django)
from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django.views.generic.base import RedirectView

# 3. Grup: Yerel uygulama modülleri
from investments import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('', views.portfolio_dashboard, name='dashboard'),
    
    path('export-sales/', views.export_sales_csv, name='export_sales'),
    
    re_path(r'^(?P<filename>.+\.(?:png|jpg|jpeg|gif|ico|svg))$', 
           lambda request, filename: RedirectView.as_view(url=settings.STATIC_URL + filename)(request)),    
]
