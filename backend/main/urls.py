from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from main import auth_views, payment_views, views

router = DefaultRouter()
router.register("books", views.BookViewSet, basename="book")

urlpatterns = [
    path("", include(router.urls)),
    path("health/", views.HealthView.as_view(), name="api_health"),
    # OpenAPI schema + interactive docs
    path("schema/", SpectacularAPIView.as_view(), name="api_schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api_schema"), name="api_docs"),
    # Auth. Tokens travel only in httpOnly cookies.
    path("auth/csrf/", auth_views.CsrfView.as_view(), name="api_csrf"),
    path("auth/register/", auth_views.RegisterView.as_view(), name="api_register"),
    path("auth/login/", auth_views.LoginView.as_view(), name="api_login"),
    path("auth/refresh/", auth_views.RefreshView.as_view(), name="api_refresh"),
    path("auth/logout/", auth_views.LogoutView.as_view(), name="api_logout"),
    path("auth/user/", auth_views.CurrentUserView.as_view(), name="api_current_user"),
    # Cart
    path("cart/", views.CartView.as_view(), name="api_cart"),
    path("cart/items/", views.CartItemsView.as_view(), name="api_cart_items"),
    path("cart/items/<int:pk>/", views.CartItemDetailView.as_view(), name="api_cart_item"),
    path("cart/checkout/", views.CheckoutView.as_view(), name="api_checkout"),
    # Orders
    path("orders/", views.OrderListView.as_view(), name="api_orders"),
    path("orders/<int:pk>/", views.OrderDetailView.as_view(), name="api_order"),
    path("orders/<int:pk>/cancel/", views.OrderCancelView.as_view(), name="api_order_cancel"),
    path("orders/<int:pk>/pay/", payment_views.PaymentStartView.as_view(), name="api_order_pay"),
    # Payments
    path("payments/config/", payment_views.PaymentConfigView.as_view(), name="api_payment_config"),
    path("payments/<int:pk>/", payment_views.PaymentDetailView.as_view(), name="api_payment"),
    path(
        "payments/<int:pk>/demo-confirm/",
        payment_views.DemoConfirmView.as_view(),
        name="api_payment_demo_confirm",
    ),
    path(
        "payments/stripe/webhook/",
        payment_views.StripeWebhookView.as_view(),
        name="api_stripe_webhook",
    ),
]
