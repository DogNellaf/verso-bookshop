from decimal import Decimal

from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APITestCase as BaseAPITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from main.authentication import ACCESS_COOKIE
from main.models import Book


def authenticate(client, user):
    """Sign the test client in the same way the SPA is signed in."""
    client.cookies[ACCESS_COOKIE] = str(RefreshToken.for_user(user).access_token)


def sign_out(client):
    client.cookies.pop(ACCESS_COOKIE, None)


def make_book(**kwargs):
    defaults = dict(
        title="Test Book",
        author="Test Author",
        description="Some description.",
        price=Decimal("29.99"),
        stock=10,
    )
    defaults.update(kwargs)
    return Book.objects.create(**defaults)


def make_user(username="testuser", password="testpass123"):
    return User.objects.create_user(username, password=password)


class APITestCase(BaseAPITestCase):
    """Resets the throttle counters (stored in the cache) between tests."""

    def setUp(self):
        cache.clear()


class AuthedAPITestCase(APITestCase):
    """APITestCase with a signed-in user (JWT in the access cookie)."""

    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.authenticate(self.user)

    def authenticate(self, user):
        authenticate(self.client, user)


def checkout_payload(**overrides):
    """A valid checkout form for the default shipping zones."""
    payload = {
        "full_name": "Test User",
        "address_line1": "1 Main Street",
        "city": "Springfield",
        "region": "OR",  # no sales tax
        "postal_code": "97403",
        "country": "US",
        "shipping_method": "standard",
    }
    payload.update(overrides)
    return payload


def checkout(client, headers=None, **overrides):
    from django.urls import reverse

    return client.post(
        reverse("api_checkout"), checkout_payload(**overrides), format="json", **(headers or {})
    )
