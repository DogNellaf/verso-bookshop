import tempfile
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase as BaseAPITestCase

from main.models import Book, BookTranslation, Cart, CartItem, Order, OrderItem

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


class APITestCase(BaseAPITestCase):
    """Resets the throttle counters (stored in the cache) between tests."""

    def setUp(self):
        cache.clear()


class AuthedAPITestCase(APITestCase):
    """APITestCase that authenticates a user via JWT."""

    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.authenticate(self.user)

    def authenticate(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


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


class CartModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.cart = Cart.objects.create(buyer=self.user)
        self.book = make_book(price=Decimal("10.00"))
        CartItem.objects.create(cart=self.cart, book=self.book, quantity=3)

    def test_total_price(self):
        self.assertEqual(self.cart.total_price, Decimal("30.00"))

    def test_total_quantity(self):
        self.assertEqual(self.cart.total_quantity, 3)

    def test_item_subtotal(self):
        item = self.cart.items.first()
        self.assertEqual(item.subtotal, Decimal("30.00"))


class OrderModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.book = make_book(price=Decimal("15.00"))
        self.order = Order.objects.create(buyer=self.user)
        OrderItem.objects.create(
            order=self.order,
            book=self.book,
            title=self.book.title,
            unit_price=Decimal("15.00"),
            quantity=2,
        )

    def test_recalculate_total(self):
        self.assertEqual(self.order.recalculate_total(), Decimal("30.00"))

    def test_item_count(self):
        self.assertEqual(self.order.item_count, 2)

    def test_default_status_pending(self):
        self.assertEqual(self.order.status, Order.Status.PENDING)

    def test_default_ordering_newest_first(self):
        self.assertEqual(Order._meta.ordering, ["-created_at"])


# ---------------------------------------------------------------------------
# API tests — books
# ---------------------------------------------------------------------------


class BookApiTest(APITestCase):
    def test_list_is_public(self):
        make_book(title="Django for Beginners")
        response = self.client.get(reverse("book-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [b["title"] for b in response.data["results"]]
        self.assertIn("Django for Beginners", titles)

    def test_search(self):
        make_book(title="The Pragmatic Programmer", author="Hunt")
        make_book(title="Clean Code", author="Martin")
        response = self.client.get(reverse("book-list"), {"search": "pragmatic"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "The Pragmatic Programmer")

    def test_pagination(self):
        for i in range(15):
            make_book(title=f"Book {i:02d}")
        response = self.client.get(reverse("book-list"))
        self.assertIsNotNone(response.data["next"])
        self.assertEqual(response.data["count"], 15)
        self.assertEqual(response.data["total_pages"], 2)

    def test_write_methods_not_allowed(self):
        # Authenticate so we reach the method check (405) rather than 401.
        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken.for_user(make_user()).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        book = make_book()
        self.assertEqual(
            self.client.post(reverse("book-list"), {"title": "Hack"}).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.delete(reverse("book-detail", args=[book.pk])).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )


# ---------------------------------------------------------------------------
# API tests — auth (JWT)
# ---------------------------------------------------------------------------


class AuthApiTest(APITestCase):
    def test_register_returns_tokens(self):
        response = self.client.post(
            reverse("api_register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password": "SecurePass!99",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            reverse("api_register"),
            {
                "username": "weakuser",
                "email": "w@example.com",
                "password": "123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="weakuser").exists())

    def test_token_obtain(self):
        make_user()
        response = self.client.post(
            reverse("api_token"),
            {
                "username": "testuser",
                "password": "testpass123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_current_user_requires_auth(self):
        self.assertEqual(
            self.client.get(reverse("api_current_user")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_current_user_with_token(self):
        user = make_user()
        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get(reverse("api_current_user"))
        self.assertEqual(response.data["username"], "testuser")


# ---------------------------------------------------------------------------
# API tests — cart
# ---------------------------------------------------------------------------


class CartApiTest(AuthedAPITestCase):
    def setUp(self):
        super().setUp()
        self.book = make_book(price=Decimal("20.00"), stock=5)

    def test_cart_starts_empty(self):
        response = self.client.get(reverse("api_cart"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["total_quantity"], 0)

    def test_add_item(self):
        response = self.client.post(
            reverse("api_cart_items"), {"book": self.book.pk, "quantity": 2}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["total_quantity"], 2)
        self.assertEqual(Decimal(response.data["total_price"]), Decimal("40.00"))

    def test_add_same_book_twice_increments(self):
        self.client.post(reverse("api_cart_items"), {"book": self.book.pk, "quantity": 2})
        self.client.post(reverse("api_cart_items"), {"book": self.book.pk, "quantity": 1})
        response = self.client.get(reverse("api_cart"))
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["quantity"], 3)

    def test_add_beyond_stock_rejected(self):
        response = self.client.post(
            reverse("api_cart_items"), {"book": self.book.pk, "quantity": 99}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_item_quantity(self):
        self.client.post(reverse("api_cart_items"), {"book": self.book.pk, "quantity": 1})
        item_id = self.client.get(reverse("api_cart")).data["items"][0]["id"]
        response = self.client.patch(reverse("api_cart_item", args=[item_id]), {"quantity": 4})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"][0]["quantity"], 4)

    def test_remove_item(self):
        self.client.post(reverse("api_cart_items"), {"book": self.book.pk, "quantity": 1})
        item_id = self.client.get(reverse("api_cart")).data["items"][0]["id"]
        response = self.client.delete(reverse("api_cart_item", args=[item_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])

    def test_cart_requires_auth(self):
        self.client.credentials()  # drop token
        self.assertEqual(
            self.client.get(reverse("api_cart")).status_code, status.HTTP_401_UNAUTHORIZED
        )


# ---------------------------------------------------------------------------
# API tests — checkout & orders
# ---------------------------------------------------------------------------


class CheckoutApiTest(AuthedAPITestCase):
    def setUp(self):
        super().setUp()
        self.book_a = make_book(title="Book A", price=Decimal("10.00"), stock=5)
        self.book_b = make_book(title="Book B", price=Decimal("25.00"), stock=3)

    def _add(self, book, qty):
        return self.client.post(reverse("api_cart_items"), {"book": book.pk, "quantity": qty})

    def test_checkout_creates_order_and_decrements_stock(self):
        self._add(self.book_a, 2)
        self._add(self.book_b, 1)
        response = self.client.post(reverse("api_checkout"))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["items"]), 2)
        self.assertEqual(Decimal(response.data["total"]), Decimal("45.00"))

        self.book_a.refresh_from_db()
        self.book_b.refresh_from_db()
        self.assertEqual(self.book_a.stock, 3)
        self.assertEqual(self.book_b.stock, 2)

    def test_checkout_clears_cart(self):
        self._add(self.book_a, 1)
        self.client.post(reverse("api_checkout"))
        self.assertEqual(self.client.get(reverse("api_cart")).data["items"], [])

    def test_checkout_snapshots_price(self):
        self._add(self.book_a, 1)
        self.client.post(reverse("api_checkout"))
        item = OrderItem.objects.get(title="Book A")
        self.assertEqual(item.unit_price, Decimal("10.00"))
        # Later price changes don't affect the historical order.
        self.book_a.price = Decimal("99.00")
        self.book_a.save()
        item.refresh_from_db()
        self.assertEqual(item.unit_price, Decimal("10.00"))

    def test_checkout_empty_cart_rejected(self):
        response = self.client.post(reverse("api_checkout"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_insufficient_stock_rejected(self):
        self._add(self.book_a, 2)
        # Reduce stock below the cart quantity after adding.
        self.book_a.stock = 1
        self.book_a.save()
        response = self.client.post(reverse("api_checkout"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)
        self.book_a.refresh_from_db()
        self.assertEqual(self.book_a.stock, 1)  # unchanged

    def test_orders_list_shows_only_own(self):
        self._add(self.book_a, 1)
        self.client.post(reverse("api_checkout"))
        other = make_user("other", "otherpass123")
        Order.objects.create(buyer=other)
        response = self.client.get(reverse("api_orders"))
        self.assertEqual(len(response.data), 1)

    def test_order_detail_forbidden_for_other_user(self):
        other = make_user("other", "otherpass123")
        order = Order.objects.create(buyer=other)
        response = self.client.get(reverse("api_order", args=[order.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# API tests — catalog filters & ordering
# ---------------------------------------------------------------------------


class BookFilterApiTest(APITestCase):
    def setUp(self):
        super().setUp()
        make_book(title="Cheap", price=Decimal("5.00"), stock=3)
        make_book(title="Pricey", price=Decimal("50.00"), stock=0)
        make_book(title="Middle", price=Decimal("20.00"), stock=1)

    def titles(self, **params):
        response = self.client.get(reverse("book-list"), params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [b["title"] for b in response.data["results"]]

    def test_in_stock_filter(self):
        self.assertEqual(self.titles(in_stock="true"), ["Cheap", "Middle"])
        self.assertEqual(self.titles(in_stock="false"), ["Pricey"])

    def test_price_range_filter(self):
        self.assertEqual(self.titles(min_price="10", max_price="30"), ["Middle"])

    def test_ordering_by_price(self):
        self.assertEqual(self.titles(ordering="-price"), ["Pricey", "Middle", "Cheap"])


# ---------------------------------------------------------------------------
# API tests — order cancellation
# ---------------------------------------------------------------------------


class OrderCancelApiTest(AuthedAPITestCase):
    def setUp(self):
        super().setUp()
        self.book = make_book(price=Decimal("10.00"), stock=5)
        self.client.post(reverse("api_cart_items"), {"book": self.book.pk, "quantity": 2})
        self.order_id = self.client.post(reverse("api_checkout")).data["id"]

    def test_cancel_pending_order_restores_stock(self):
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 3)

        response = self.client.post(reverse("api_order_cancel", args=[self.order_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Order.Status.CANCELLED)

        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 5)

    def test_cannot_cancel_twice(self):
        self.client.post(reverse("api_order_cancel", args=[self.order_id]))
        response = self.client.post(reverse("api_order_cancel", args=[self.order_id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 5)  # restored only once

    def test_cannot_cancel_shipped_order(self):
        Order.objects.filter(pk=self.order_id).update(status=Order.Status.SHIPPED)
        response = self.client.post(reverse("api_order_cancel", args=[self.order_id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_cancel_other_users_order(self):
        self.authenticate(make_user("other", "otherpass123"))
        response = self.client.post(reverse("api_order_cancel", args=[self.order_id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel_survives_deleted_book(self):
        self.book.delete()
        response = self.client.post(reverse("api_order_cancel", args=[self.order_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# API tests — performance, docs, health, throttling
# ---------------------------------------------------------------------------


class CartQueryCountTest(AuthedAPITestCase):
    def test_cart_query_count_does_not_grow_with_items(self):
        cart = Cart.objects.create(buyer=self.user)
        for i in range(5):
            CartItem.objects.create(cart=cart, book=make_book(title=f"B{i}"), quantity=1)
        # user, cart, items+books in one JOIN, book translations — independent
        # of the item count.
        with self.assertNumQueries(4):
            response = self.client.get(reverse("api_cart"))
        self.assertEqual(len(response.data["items"]), 5)


class InfraApiTest(APITestCase):
    def test_health(self):
        response = self.client.get(reverse("api_health"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok"})

    def test_openapi_schema(self):
        response = self.client.get(reverse("api_schema"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"/api/cart/checkout/", response.content)

    def test_swagger_ui(self):
        self.assertEqual(self.client.get(reverse("api_docs")).status_code, status.HTTP_200_OK)


class ThrottleTest(APITestCase):
    @override_settings(
        REST_FRAMEWORK={
            **__import__("django.conf").conf.settings.REST_FRAMEWORK,
            "DEFAULT_THROTTLE_RATES": {"anon": "100/min", "user": "100/min", "auth": "2/min"},
        }
    )
    def test_login_is_rate_limited(self):
        from rest_framework.settings import api_settings
        from rest_framework.throttling import ScopedRateThrottle

        api_settings.reload()
        ScopedRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
        try:
            payload = {"username": "nobody", "password": "wrong"}
            codes = [self.client.post(reverse("api_token"), payload).status_code for _ in range(3)]
            self.assertEqual(codes[:2], [401, 401])
            self.assertEqual(codes[2], status.HTTP_429_TOO_MANY_REQUESTS)
        finally:
            api_settings.reload()
            ScopedRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES


# ---------------------------------------------------------------------------
# API tests — localization
# ---------------------------------------------------------------------------


class LocalizationApiTest(AuthedAPITestCase):
    def checkout_error(self, language=None):
        headers = {"HTTP_ACCEPT_LANGUAGE": language} if language else {}
        return self.client.post(reverse("api_checkout"), **headers).data["detail"]

    def test_english_by_default(self):
        self.assertEqual(self.checkout_error(), "Your cart is empty.")

    def test_messages_follow_the_requested_language(self):
        self.assertEqual(self.checkout_error("ru"), "Ваша корзина пуста.")
        self.assertEqual(self.checkout_error("fr"), "Votre panier est vide.")
        self.assertEqual(self.checkout_error("de"), "Ihr Warenkorb ist leer.")

    def test_unsupported_language_falls_back_to_english(self):
        self.assertEqual(self.checkout_error("ja"), "Your cart is empty.")

    def test_stock_message_uses_plural_forms(self):
        book = make_book(title="Dune", stock=2)
        response = self.client.post(
            reverse("api_cart_items"),
            {"book": book.pk, "quantity": 5},
            HTTP_ACCEPT_LANGUAGE="ru",
        )
        self.assertEqual(str(response.data["quantity"]), "Осталось только 2 экземпляра «Dune».")

        book.stock = 5
        book.save()
        response = self.client.post(
            reverse("api_cart_items"),
            {"book": book.pk, "quantity": 9},
            HTTP_ACCEPT_LANGUAGE="ru",
        )
        self.assertEqual(str(response.data["quantity"]), "Осталось только 5 экземпляров «Dune».")

    def test_out_of_stock_message(self):
        book = make_book(title="Dune", stock=0)
        response = self.client.post(
            reverse("api_cart_items"), {"book": book.pk}, HTTP_ACCEPT_LANGUAGE="de"
        )
        self.assertEqual(str(response.data["quantity"]), "„Dune“ ist nicht vorrätig.")


class CatalogTranslationApiTest(AuthedAPITestCase):
    def setUp(self):
        super().setUp()
        self.crime = make_book(title="Crime and Punishment", author="Fyodor Dostoevsky")
        BookTranslation.objects.create(
            book=self.crime,
            language="ru",
            title="Преступление и наказание",
            author="Фёдор Достоевский",
            description="Роман о студенте Раскольникове.",
        )
        self.animal = make_book(title="Animal Farm", author="George Orwell")
        BookTranslation.objects.create(
            book=self.animal,
            language="ru",
            title="Скотный двор",
            author="Джордж Оруэлл",
            description="Сказка о революции.",
        )

    def get(self, url, language, **params):
        return self.client.get(url, params, HTTP_ACCEPT_LANGUAGE=language).data

    def test_book_is_returned_in_the_requested_language(self):
        data = self.get(reverse("book-detail", args=[self.crime.pk]), "ru")
        self.assertEqual(data["title"], "Преступление и наказание")
        self.assertEqual(data["author"], "Фёдор Достоевский")
        self.assertEqual(data["description"], "Роман о студенте Раскольникове.")

    def test_missing_translation_falls_back_to_english(self):
        data = self.get(reverse("book-detail", args=[self.crime.pk]), "de")
        self.assertEqual(data["title"], "Crime and Punishment")

    def test_search_matches_translated_titles(self):
        data = self.get(reverse("book-list"), "en", search="наказание")
        self.assertEqual([b["title"] for b in data["results"]], ["Crime and Punishment"])

    def test_ordering_uses_translated_titles(self):
        english = self.get(reverse("book-list"), "en")
        russian = self.get(reverse("book-list"), "ru")
        self.assertEqual(
            [b["title"] for b in english["results"]], ["Animal Farm", "Crime and Punishment"]
        )
        self.assertEqual(
            [b["title"] for b in russian["results"]], ["Преступление и наказание", "Скотный двор"]
        )

    def test_cart_and_orders_show_translated_books(self):
        self.client.post(reverse("api_cart_items"), {"book": self.crime.pk})
        cart = self.get(reverse("api_cart"), "ru")
        self.assertEqual(cart["items"][0]["book"]["title"], "Преступление и наказание")

        self.client.post(reverse("api_checkout"))
        orders = self.get(reverse("api_orders"), "ru")
        self.assertEqual(orders[0]["items"][0]["book"]["title"], "Преступление и наказание")
        # The order line keeps its purchase-time snapshot.
        self.assertEqual(orders[0]["items"][0]["title"], "Crime and Punishment")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="verso-media-"))
class SeedCommandTest(TestCase):
    def test_seed_is_idempotent_and_translates_the_catalog(self):
        from django.core.management import call_command

        call_command("seed", "--no-covers", stdout=StringIO())
        call_command("seed", "--no-covers", stdout=StringIO())

        # Every demo book has a cover bundled in the repository.
        self.assertEqual(Book.objects.exclude(cover="").count(), 18)

        self.assertEqual(Book.objects.count(), 18)
        self.assertEqual(BookTranslation.objects.count(), 18 * 3)
        self.assertEqual(Order.objects.filter(buyer__username="demo").count(), 3)
        crime = BookTranslation.objects.get(book__title="Crime and Punishment", language="ru")
        self.assertEqual(crime.title, "Преступление и наказание")

    def test_bundled_covers_are_used_offline(self):
        from pathlib import Path
        from unittest import mock

        from django.core.management import call_command

        covers = Path(tempfile.mkdtemp(prefix="verso-covers-"))
        (covers / "9780451524935.jpg").write_bytes(b"\xff\xd8" + b"0" * 2000)  # 1984
        with mock.patch("main.management.commands.seed.BUNDLED_COVERS", covers):
            call_command("seed", "--no-covers", stdout=StringIO())

        self.assertTrue(Book.objects.get(title="1984").cover.name.endswith(".jpg"))
        self.assertFalse(Book.objects.get(title="Dracula").cover)

    def test_downloaded_covers_can_be_saved_for_offline_use(self):
        from pathlib import Path
        from unittest import mock

        from django.core.management import call_command

        covers = Path(tempfile.mkdtemp(prefix="verso-covers-")) / "covers"
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"\xff\xd8" + b"0" * 2000
        with (
            mock.patch("main.management.commands.seed.BUNDLED_COVERS", covers),
            mock.patch("urllib.request.urlopen", return_value=response),
        ):
            call_command("seed", "--save-covers", stdout=StringIO())

        self.assertEqual(len(list(covers.glob("*.jpg"))), 18)
        self.assertEqual(Book.objects.exclude(cover="").count(), 18)

    def test_flush_and_failed_downloads(self):
        from pathlib import Path
        from unittest import mock
        from urllib.error import URLError

        from django.core.management import call_command

        make_book(title="Leftover")
        no_bundled = Path(tempfile.mkdtemp(prefix="verso-covers-"))
        with (
            mock.patch("main.management.commands.seed.BUNDLED_COVERS", no_bundled),
            mock.patch("urllib.request.urlopen", side_effect=URLError("offline")),
        ):
            call_command("seed", "--flush", stdout=StringIO())

        self.assertFalse(Book.objects.filter(title="Leftover").exists())
        self.assertEqual(Book.objects.exclude(cover="").count(), 0)
