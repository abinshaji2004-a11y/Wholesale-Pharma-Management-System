from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, BrandViewSet, ManufacturerViewSet, ProductViewSet, PurchaseBillViewSet, WishlistView, LowStockAlertView, NearExpiryAlertView, SupplierViewSet, GoodsReceivedNoteViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'brands', BrandViewSet)
router.register(r'manufacturers', ManufacturerViewSet)
router.register(r'products', ProductViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'grn', GoodsReceivedNoteViewSet)
router.register(r'purchases', PurchaseBillViewSet, basename='purchases')

urlpatterns = [
    path('wishlist/', WishlistView.as_view(), name='wishlist'),
    path('alerts/low-stock/', LowStockAlertView.as_view(), name='low-stock-alerts'),
    path('alerts/near-expiry/', NearExpiryAlertView.as_view(), name='near-expiry-alerts'),
    path('', include(router.urls)),
]
