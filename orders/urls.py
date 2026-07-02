from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CartView, CheckoutView, OrderViewSet, ReturnViewSet, QuickBillingView, BulkOrderUploadView, PowerBIReportView, InvoicePDFView, ExportOrdersExcelView, AdminReturnsView

router = DefaultRouter()
router.register(r'history', OrderViewSet, basename='order')
router.register(r'returns', ReturnViewSet, basename='returns')

urlpatterns = [
    path('admin-returns/', AdminReturnsView.as_view(), name='admin_returns'),
    path('cart/', CartView.as_view(), name='cart'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('quick-bill/', QuickBillingView.as_view(), name='quick_bill'),
    path('bulk-upload/', BulkOrderUploadView.as_view(), name='bulk-upload'),
    path('reports/power-bi/', PowerBIReportView.as_view(), name='power-bi-report'),
    path('export/excel/', ExportOrdersExcelView.as_view(), name='export-excel'),
    path('<int:pk>/invoice/pdf/', InvoicePDFView.as_view(), name='invoice-pdf'),
    path('', include(router.urls)),
]
