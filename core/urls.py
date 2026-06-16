from django.contrib import admin
from django.urls import path
from investments import views
from django.conf import settings
from django.urls import path, re_path
from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('', views.portfolio_dashboard, name='dashboard'),
    
    path('export-sales/', views.export_sales_csv, name='export_sales'),
    
    re_path(r'^(?P<filename>.+\.(?:png|jpg|jpeg|gif|ico|svg))$', 
           lambda request, filename: RedirectView.as_view(url=settings.STATIC_URL + filename)(request)),    
]
