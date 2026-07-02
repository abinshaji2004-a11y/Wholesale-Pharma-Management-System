from django.urls import path
from .views import RegisterView, LoginView, UserProfileView, AdminDealerApprovalView, AdminPendingDealersView, AdminUserUsernameUpdateView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('admin/pending-dealers/', AdminPendingDealersView.as_view(), name='pending_dealers'),
    path('dealer/<int:user_id>/approve/', AdminDealerApprovalView.as_view(), name='dealer_approve'),
    path('admin/update-username/', AdminUserUsernameUpdateView.as_view(), name='admin_update_username'),
]
