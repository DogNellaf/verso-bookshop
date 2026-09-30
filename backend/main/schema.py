"""OpenAPI description of the cookie authentication."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension

from main.authentication import ACCESS_COOKIE


class CookieJWTScheme(OpenApiAuthenticationExtension):
    target_class = "main.authentication.CookieJWTAuthentication"
    name = "jwtCookie"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": ACCESS_COOKIE,
            "description": (
                "Set by POST /api/auth/login/. Unsafe requests also need the "
                "X-CSRFToken header with the value of the csrftoken cookie."
            ),
        }
