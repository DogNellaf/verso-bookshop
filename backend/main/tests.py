from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from main.models import Book, Order


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class BookModelTest(TestCase):
    def setUp(self):
        self.book = make_book()

    def test_str(self):
        self.assertEqual(str(self.book), "Test Book — Test Author")

    def test_in_stock_true(self):
        self.assertTrue(self.book.in_stock)

    def test_in_stock_false_when_zero(self):
        self.book.stock = 0
        self.book.save()
        self.assertFalse(self.book.in_stock)

    def test_default_ordering_by_title(self):
        make_book(title="Aardvark")
        make_book(title="Zebra")
        titles = list(Book.objects.values_list("title", flat=True))
        self.assertEqual(titles, sorted(titles))


class OrderModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.book = make_book(price=Decimal("29.99"))
        self.order = Order.objects.create(buyer=self.user, book=self.book, quantity=2)

    def test_str(self):
        self.assertEqual(str(self.order), "testuser — Test Book × 2")

    def test_total_price(self):
        self.assertEqual(self.order.total_price, Decimal("59.98"))

    def test_created_at_set_automatically(self):
        self.assertIsNotNone(self.order.created_at)

    def test_default_ordering_newest_first(self):
        self.assertEqual(Order._meta.ordering, ["-created_at"])


# ---------------------------------------------------------------------------
# API tests — books
# ---------------------------------------------------------------------------

class BookApiTest(APITestCase):
    def test_empty_catalog(self):
        response = self.client.get(reverse("book-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    def test_books_listed(self):
        make_book(title="Django for Beginners")
        response = self.client.get(reverse("book-list"))
        titles = [b["title"] for b in response.data["results"]]
        self.assertIn("Django for Beginners", titles)

    def test_out_of_stock_flagged(self):
        book = make_book(title="Gone Book", stock=0)
        response = self.client.get(reverse("book-detail", args=[book.pk]))
        self.assertFalse(response.data["in_stock"])

    def test_pagination(self):
        for i in range(12):
            make_book(title=f"Book {i:02d}")
        response = self.client.get(reverse("book-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["next"])

    def test_detail_ok(self):
        book = make_book(title="Detail Book", description="Full description here.")
        response = self.client.get(reverse("book-detail", args=[book.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Detail Book")

    def test_404_for_missing_book(self):
        response = self.client.get(reverse("book-detail", args=[99999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_write_methods_not_allowed(self):
        book = make_book()
        response = self.client.post(reverse("book-list"), {"title": "Hack"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        response = self.client.delete(reverse("book-detail", args=[book.pk]))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ---------------------------------------------------------------------------
# API tests — register
# ---------------------------------------------------------------------------

class RegisterApiTest(APITestCase):
    def test_valid_registration_creates_user_and_logs_in(self):
        response = self.client.post(reverse("api_register"), {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePass!99",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())
        me = self.client.get(reverse("api_current_user"))
        self.assertEqual(me.data["username"], "newuser")

    def test_duplicate_username_rejected(self):
        make_user()
        response = self.client.post(reverse("api_register"), {
            "username": "testuser",
            "email": "x@x.com",
            "password": "SecurePass!99",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_password_rejected(self):
        response = self.client.post(reverse("api_register"), {
            "username": "newuser",
            "email": "newuser@example.com",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="newuser").exists())


# ---------------------------------------------------------------------------
# API tests — login / logout / current user
# ---------------------------------------------------------------------------

class AuthApiTest(APITestCase):
    def setUp(self):
        self.user = make_user()

    def test_valid_login(self):
        response = self.client.post(reverse("api_login"), {
            "username": "testuser",
            "password": "testpass123",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "testuser")

    def test_invalid_credentials(self):
        response = self.client.post(reverse("api_login"), {
            "username": "testuser",
            "password": "wrongpassword",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_current_user_unauthenticated(self):
        response = self.client.get(reverse("api_current_user"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_current_user_authenticated(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("api_current_user"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "testuser")

    def test_logout_clears_session(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(reverse("api_logout"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        me = self.client.get(reverse("api_current_user"))
        self.assertEqual(me.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# API tests — orders
# ---------------------------------------------------------------------------

class OrderApiTest(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.book = make_book(price=Decimal("25.00"), stock=10)
        self.client.login(username="testuser", password="testpass123")

    def test_valid_order_creates_record_and_reduces_stock(self):
        response = self.client.post(reverse("api_orders"), {
            "book": self.book.pk,
            "quantity": 3,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 7)
        self.assertEqual(Order.objects.filter(buyer=self.user).count(), 1)

    def test_order_exceeds_stock_rejected(self):
        response = self.client.post(reverse("api_orders"), {
            "book": self.book.pk,
            "quantity": 100,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 10)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("api_orders"), {
            "book": self.book.pk,
            "quantity": 1,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_lists_only_own_orders(self):
        other = User.objects.create_user("other", password="otherpass123")
        Order.objects.create(buyer=other, book=self.book, quantity=1)
        Order.objects.create(buyer=self.user, book=self.book, quantity=2)
        response = self.client.get(reverse("api_orders"))
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["quantity"], 2)
