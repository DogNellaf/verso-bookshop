from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Session auth without CSRF enforcement, for the SPA which authenticates
    via fetch/axios and does not carry a CSRF token."""

    def enforce_csrf(self, request):
        return None
