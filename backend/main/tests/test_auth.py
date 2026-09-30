from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from main.authentication import ACCESS_COOKIE, REFRESH_COOKIE, SESSION_HINT_COOKIE
from main.tests.helpers import APITestCase, make_user

CREDENTIALS = {"username": "testuser", "password": "testpass123"}


class CookieAuthTest(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()

    def login(self):
        response = self.client.post(reverse("api_login"), CREDENTIALS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response

    def test_login_sets_httponly_cookies_and_returns_no_tokens(self):
        response = self.login()
        self.assertEqual(response.data["username"], "testuser")
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)

        access = response.cookies[ACCESS_COOKIE]
        refresh = response.cookies[REFRESH_COOKIE]
        self.assertTrue(access["httponly"])
        self.assertTrue(refresh["httponly"])
        self.assertEqual(access["samesite"], "Lax")
        self.assertEqual(refresh["path"], "/api/auth/")
        # The hint cookie is readable by JavaScript and carries no secret.
        self.assertFalse(response.cookies[SESSION_HINT_COOKIE]["httponly"])
        self.assertEqual(response.cookies[SESSION_HINT_COOKIE].value, "1")

    def test_cookie_authenticates_requests(self):
        self.login()
        response = self.client.get(reverse("api_current_user"))
        self.assertEqual(response.data["username"], "testuser")

    def test_wrong_password(self):
        response = self.client.post(
            reverse("api_login"), {"username": "testuser", "password": "nope"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn(ACCESS_COOKIE, response.cookies)

    def test_register_signs_the_user_in(self):
        response = self.client.post(
            reverse("api_register"),
            {"username": "newuser", "email": "new@example.com", "password": "SecurePass!99"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "newuser")
        self.assertIn(ACCESS_COOKIE, response.cookies)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            reverse("api_register"),
            {"username": "weakuser", "email": "w@example.com", "password": "123"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="weakuser").exists())

    def test_refresh_rotates_and_blacklists_the_old_token(self):
        self.login()
        old_refresh = self.client.cookies[REFRESH_COOKIE].value

        response = self.client.post(reverse("api_refresh"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotEqual(response.cookies[REFRESH_COOKIE].value, old_refresh)
        self.assertEqual(BlacklistedToken.objects.count(), 1)

        # Replaying the old refresh token fails and clears the cookies.
        self.client.cookies[REFRESH_COOKIE] = old_refresh
        replay = self.client.post(reverse("api_refresh"))
        self.assertEqual(replay.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(replay.cookies[ACCESS_COOKIE].value, "")

    def test_refresh_without_cookie(self):
        response = self.client.post(reverse("api_refresh"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_clears_cookies_and_revokes_the_refresh_token(self):
        self.login()
        refresh = self.client.cookies[REFRESH_COOKIE].value
        response = self.client.post(reverse("api_logout"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.cookies[ACCESS_COOKIE].value, "")
        self.assertEqual(response.cookies[REFRESH_COOKIE].value, "")

        self.client.cookies[REFRESH_COOKIE] = refresh
        self.assertEqual(
            self.client.post(reverse("api_refresh")).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_expired_or_broken_access_cookie_counts_as_anonymous(self):
        self.client.cookies[ACCESS_COOKIE] = "not-a-jwt"
        self.assertEqual(self.client.get(reverse("book-list")).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.get(reverse("api_current_user")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authorization_header_is_not_accepted(self):
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(
            self.client.get(reverse("api_current_user")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class CsrfTest(APITestCase):
    """The browser sends cookies automatically, so unsafe requests need a CSRF token."""

    def setUp(self):
        super().setUp()
        make_user()
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf_token(self):
        response = self.client.get(reverse("api_csrf"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        return self.client.cookies["csrftoken"].value

    def test_login_without_csrf_token_is_rejected(self):
        response = self.client.post(reverse("api_login"), CREDENTIALS)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_and_cart_with_csrf_token(self):
        token = self.csrf_token()
        response = self.client.post(reverse("api_login"), CREDENTIALS, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Safe methods need no token, unsafe ones do.
        self.assertEqual(self.client.get(reverse("api_cart")).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.post(reverse("api_checkout")).status_code, status.HTTP_403_FORBIDDEN
        )
        self.assertEqual(
            self.client.post(reverse("api_checkout"), HTTP_X_CSRFTOKEN=token).status_code,
            status.HTTP_400_BAD_REQUEST,  # empty cart, but past the CSRF check
        )
