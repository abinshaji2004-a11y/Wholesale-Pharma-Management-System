"""
URL configuration for abin_pharma project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from .views import home_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/orders/', include('orders.urls')),
    
    path('', home_view, name='home'),
    path('products/', TemplateView.as_view(template_name='products.html'), name='products'),
    path('shop/', TemplateView.as_view(template_name='shop.html'), name='shop'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    path('contact/', TemplateView.as_view(template_name='contact.html'), name='contact'),
    path('profile/', TemplateView.as_view(template_name='customer-profile.html'), name='profile'),
    path('dashboard/', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    path('login/', TemplateView.as_view(template_name='login.html'), name='login_page'),
    path('customer-login/', TemplateView.as_view(template_name='customer-login.html'), name='customer_login'),
    path('cart/', TemplateView.as_view(template_name='cart.html'), name='cart_page'),
    path('bulk-upload/', TemplateView.as_view(template_name='bulk_order.html'), name='bulk-upload'),
    path('admin-dashboard/', TemplateView.as_view(template_name='admin-dashboard.html'), name='admin_dashboard'),
    path('admin-returns/', TemplateView.as_view(template_name='admin-returns.html'), name='admin_returns_page'),
    path('sales/', TemplateView.as_view(template_name='sales.html'), name='sales'),
    path('purchases/', TemplateView.as_view(template_name='purchases.html'), name='purchases'),
    path('draft-medicines/', TemplateView.as_view(template_name='drafts.html'), name='drafts_page'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
