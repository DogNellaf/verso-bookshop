from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from main import views

router = DefaultRouter()
router.register("books", views.BookViewSet, basename="book")

urlpatterns = [
    path("", include(router.urls)),
    path("health/", views.HealthView.as_view(), name="api_health"),
    # OpenAPI schema + interactive docs
    path("schema/", SpectacularAPIView.as_view(), name="api_schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api_schema"), name="api_docs"),
    # Auth (JWT)
    path("auth/register/", views.RegisterView.as_view(), name="api_register"),
    path("auth/token/", views.ThrottledTokenObtainPairView.as_view(), name="api_token"),
    path(
        "auth/token/refresh/",
        views.ThrottledTokenRefreshView.as_view(),
        name="api_token_refresh",
    ),
    path("auth/user/", views.CurrentUserView.as_view(), name="api_current_user"),
    # Cart
    path("cart/", views.CartView.as_view(), name="api_cart"),
    path("cart/items/", views.CartItemsView.as_view(), name="api_cart_items"),
    path("cart/items/<int:pk>/", views.CartItemDetailView.as_view(), name="api_cart_item"),
    path("cart/checkout/", views.CheckoutView.as_view(), name="api_checkout"),
    # Orders
    path("orders/", views.OrderListView.as_view(), name="api_orders"),
    path("orders/<int:pk>/", views.OrderDetailView.as_view(), name="api_order"),
    path("orders/<int:pk>/cancel/", views.OrderCancelView.as_view(), name="api_order_cancel"),
]
