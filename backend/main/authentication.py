"""JWT authentication through httpOnly cookies.

The access and refresh tokens never reach JavaScript. The browser sends them
as cookies, so every unsafe request also has to pass Django's CSRF check.
"""

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

ACCESS_COOKIE = "verso_access"
REFRESH_COOKIE = "verso_refresh"
# Readable by JavaScript and holds no secret. It only tells the SPA that a
# session probably exists, so anonymous visitors skip the /auth/user/ call.
SESSION_HINT_COOKIE = "verso_session"

ACCESS_PATH = "/api/"
REFRESH_PATH = "/api/auth/"


class _CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        return reason


def enforce_csrf(request):
    """Run Django's CSRF check on a DRF request, as SessionAuthentication does."""

    def dummy_get_response(request):  # pragma: no cover
        return None

    check = _CSRFCheck(dummy_get_response)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")


class CookieJWTAuthentication(JWTAuthentication):
    """Reads the access token from a cookie and enforces CSRF.

    An expired or broken token is treated as "not signed in" instead of an
    error, so public pages keep working and protected ones answer 401, which
    tells the SPA to refresh the session.
    """

    def authenticate(self, request):
        raw_token = request.COOKIES.get(ACCESS_COOKIE)
        if not raw_token:
            return None
        try:
            validated = self.get_validated_token(raw_token)
        except (InvalidToken, TokenError):
            return None
        user = self.get_user(validated)
        enforce_csrf(request)
        return user, validated


def _cookie_options(path):
    return {
        "httponly": True,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": "Lax",
        "path": path,
    }


def set_auth_cookies(response, refresh):
    """Put a fresh access/refresh pair into the response cookies."""
    jwt = settings.SIMPLE_JWT
    response.set_cookie(
        ACCESS_COOKIE,
        str(refresh.access_token),
        max_age=int(jwt["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        **_cookie_options(ACCESS_PATH),
    )
    response.set_cookie(
        REFRESH_COOKIE,
        str(refresh),
        max_age=int(jwt["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        **_cookie_options(REFRESH_PATH),
    )
    response.set_cookie(
        SESSION_HINT_COOKIE,
        "1",
        max_age=int(jwt["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="Lax",
        path="/",
    )
    return response


def clear_auth_cookies(response):
    response.delete_cookie(ACCESS_COOKIE, path=ACCESS_PATH, samesite="Lax")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH, samesite="Lax")
    response.delete_cookie(SESSION_HINT_COOKIE, path="/", samesite="Lax")
    return response
