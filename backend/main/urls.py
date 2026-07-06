from django.urls import include, path
from rest_framework.routers import DefaultRouter

from main import views

router = DefaultRouter()
router.register("books", views.BookViewSet, basename="book")

urlpatterns = [
    path("", include(router.urls)),
    path("register/", views.RegisterView.as_view(), name="api_register"),
    path("login/", views.LoginView.as_view(), name="api_login"),
    path("logout/", views.LogoutView.as_view(), name="api_logout"),
    path("user/", views.CurrentUserView.as_view(), name="api_current_user"),
    path("orders/", views.OrderListCreateView.as_view(), name="api_orders"),
]
