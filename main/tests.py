from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from main.forms import LoginForm, OrderForm, RegisterForm
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
# View tests — index
# ---------------------------------------------------------------------------

class IndexViewTest(TestCase):
    def test_empty_catalog(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

    def test_books_shown(self):
        make_book(title="Django for Beginners")
        response = self.client.get(reverse("index"))
        self.assertContains(response, "Django for Beginners")

    def test_out_of_stock_no_buy_button(self):
        make_book(title="Gone Book", stock=0)
        response = self.client.get(reverse("index"))
        self.assertNotContains(response, "order_book")

    def test_pagination(self):
        for i in range(12):
            make_book(title=f"Book {i:02d}")
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "page=2")


# ---------------------------------------------------------------------------
# View tests — book_detail
# ---------------------------------------------------------------------------

class BookDetailViewTest(TestCase):
    def setUp(self):
        self.book = make_book(title="Detail Book", description="Full description here.")

    def test_detail_page_ok(self):
        response = self.client.get(reverse("book_detail", args=[self.book.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail Book")
        self.assertContains(response, "Full description here.")

    def test_404_for_missing_book(self):
        response = self.client.get(reverse("book_detail", args=[99999]))
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# View tests — register
# ---------------------------------------------------------------------------

class RegisterViewTest(TestCase):
    def test_get_register_page(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)

    def test_valid_registration_creates_user_and_redirects(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "SecurePass!99",
            "password2": "SecurePass!99",
        })
        self.assertRedirects(response, reverse("index"))
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_registration_auto_logs_in(self):
        self.client.post(reverse("register"), {
            "username": "autouser",
            "email": "a@b.com",
            "password1": "SecurePass!99",
            "password2": "SecurePass!99",
        })
        response = self.client.get(reverse("index"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_password_mismatch_stays_on_page(self):
        response = self.client.post(reverse("register"), {
            "username": "baduser",
            "email": "bad@example.com",
            "password1": "SecurePass!99",
            "password2": "WrongPass!00",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="baduser").exists())

    def test_authenticated_user_redirected_away(self):
        make_user()
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("register"))
        self.assertRedirects(response, reverse("index"))


# ---------------------------------------------------------------------------
# View tests — login
# ---------------------------------------------------------------------------

class LoginViewTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_get_login_page(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_valid_login_redirects_to_index(self):
        response = self.client.post(reverse("login"), {
            "username": "testuser",
            "password": "testpass123",
        })
        self.assertRedirects(response, reverse("index"))

    def test_invalid_credentials_stay_on_page(self):
        response = self.client.post(reverse("login"), {
            "username": "testuser",
            "password": "wrongpassword",
        })
        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_redirected_away(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("login"))
        self.assertRedirects(response, reverse("index"))


# ---------------------------------------------------------------------------
# View tests — logout
# ---------------------------------------------------------------------------

class LogoutViewTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.login(username="testuser", password="testpass123")

    def test_post_logout_redirects_to_index(self):
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("index"))

    def test_post_logout_clears_session(self):
        self.client.post(reverse("logout"))
        response = self.client.get(reverse("index"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_get_logout_unauthenticated_redirects_to_login(self):
        self.client.logout()
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# View tests — order_book
# ---------------------------------------------------------------------------

class OrderBookViewTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.book = make_book(price=Decimal("25.00"), stock=10)
        self.client.login(username="testuser", password="testpass123")

    def test_get_order_form(self):
        response = self.client.get(reverse("order_book", args=[self.book.pk]))
        self.assertEqual(response.status_code, 200)

    def test_valid_order_creates_record_and_reduces_stock(self):
        response = self.client.post(
            reverse("order_book", args=[self.book.pk]),
            {"quantity": 3},
        )
        self.assertRedirects(response, reverse("my_orders"))
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 7)
        self.assertEqual(Order.objects.filter(buyer=self.user).count(), 1)

    def test_order_exceeds_stock_shows_error(self):
        response = self.client.post(
            reverse("order_book", args=[self.book.pk]),
            {"quantity": 100},
        )
        self.assertEqual(response.status_code, 200)
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 10)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("order_book", args=[self.book.pk]))
        self.assertNotEqual(response.status_code, 200)

    def test_order_404_for_missing_book(self):
        response = self.client.get(reverse("order_book", args=[99999]))
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# View tests — my_orders
# ---------------------------------------------------------------------------

class MyOrdersViewTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.book = make_book(price=Decimal("15.00"))
        self.client.login(username="testuser", password="testpass123")

    def test_orders_page_loads(self):
        response = self.client.get(reverse("my_orders"))
        self.assertEqual(response.status_code, 200)

    def test_shows_user_orders(self):
        Order.objects.create(buyer=self.user, book=self.book, quantity=2)
        response = self.client.get(reverse("my_orders"))
        self.assertContains(response, "Test Book")

    def test_does_not_show_other_users_orders(self):
        other = User.objects.create_user("other", password="otherpass123")
        Order.objects.create(buyer=other, book=self.book, quantity=1)
        response = self.client.get(reverse("my_orders"))
        self.assertNotContains(response, "Test Book")

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("my_orders"))
        self.assertNotEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# Form tests
# ---------------------------------------------------------------------------

class RegisterFormTest(TestCase):
    def test_valid_form(self):
        form = RegisterForm(data={
            "username": "formuser",
            "email": "form@example.com",
            "password1": "SecurePass!99",
            "password2": "SecurePass!99",
        })
        self.assertTrue(form.is_valid())

    def test_email_required(self):
        form = RegisterForm(data={
            "username": "formuser",
            "email": "",
            "password1": "SecurePass!99",
            "password2": "SecurePass!99",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_bootstrap_class_applied(self):
        form = RegisterForm()
        self.assertIn("form-control", form.fields["username"].widget.attrs.get("class", ""))

    def test_duplicate_username_invalid(self):
        make_user()
        form = RegisterForm(data={
            "username": "testuser",
            "email": "x@x.com",
            "password1": "SecurePass!99",
            "password2": "SecurePass!99",
        })
        self.assertFalse(form.is_valid())


class LoginFormTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_valid_credentials(self):
        factory = RequestFactory()
        request = factory.post("/login/")
        request.session = self.client.session
        form = LoginForm(request=request, data={
            "username": "testuser",
            "password": "testpass123",
        })
        self.assertTrue(form.is_valid())

    def test_bootstrap_class_applied(self):
        form = LoginForm()
        self.assertIn("form-control", form.fields["username"].widget.attrs.get("class", ""))


class OrderFormTest(TestCase):
    def test_valid_quantity(self):
        form = OrderForm(data={"quantity": 3})
        self.assertTrue(form.is_valid())

    def test_quantity_of_one_valid(self):
        form = OrderForm(data={"quantity": 1})
        self.assertTrue(form.is_valid())

    def test_zero_quantity_invalid(self):
        form = OrderForm(data={"quantity": 0})
        self.assertFalse(form.is_valid())

    def test_negative_quantity_invalid(self):
        form = OrderForm(data={"quantity": -5})
        self.assertFalse(form.is_valid())

    def test_missing_quantity_invalid(self):
        form = OrderForm(data={})
        self.assertFalse(form.is_valid())
