from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from main import views

router = DefaultRouter()
router.register("books", views.BookViewSet, basename="book")

urlpatterns = [
    path("", include(router.urls)),

    # Auth (JWT)
    path("auth/register/", views.RegisterView.as_view(), name="api_register"),
    path("auth/token/", TokenObtainPairView.as_view(), name="api_token"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="api_token_refresh"),
    path("auth/user/", views.CurrentUserView.as_view(), name="api_current_user"),

    # Cart
    path("cart/", views.CartView.as_view(), name="api_cart"),
    path("cart/items/", views.CartItemsView.as_view(), name="api_cart_items"),
    path("cart/items/<int:pk>/", views.CartItemDetailView.as_view(), name="api_cart_item"),
    path("cart/checkout/", views.CheckoutView.as_view(), name="api_checkout"),

    # Orders
    path("orders/", views.OrderListView.as_view(), name="api_orders"),
    path("orders/<int:pk>/", views.OrderDetailView.as_view(), name="api_order"),
]
