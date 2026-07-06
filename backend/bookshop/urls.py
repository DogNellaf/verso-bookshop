from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from main import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path("book/<int:pk>/", views.book_detail, name="book_detail"),
    path("book/<int:pk>/order/", views.order_book, name="order_book"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("orders/", views.my_orders, name="my_orders"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
