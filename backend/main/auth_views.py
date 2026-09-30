import contextlib

from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from main.authentication import (
    REFRESH_COOKIE,
    clear_auth_cookies,
    enforce_csrf,
    set_auth_cookies,
)
from main.serializers import RegisterSerializer, UserSerializer


class CsrfProtectedView(APIView):
    """Auth endpoints run without a signed-in user, so they check CSRF themselves."""

    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        enforce_csrf(request)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """Sets the csrftoken cookie that the SPA sends back in X-CSRFToken."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(responses={204: None})
    def get(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class LoginView(CsrfProtectedView):
    @extend_schema(request=LoginSerializer, responses=UserSerializer)
    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user
        return set_auth_cookies(Response(UserSerializer(user).data), RefreshToken.for_user(user))


class RegisterView(CsrfProtectedView):
    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return set_auth_cookies(
            Response(UserSerializer(user).data, status=status.HTTP_201_CREATED),
            RefreshToken.for_user(user),
        )


class RefreshView(CsrfProtectedView):
    """Rotates the refresh token. The old one is blacklisted."""

    @extend_schema(
        request=None,
        responses={
            204: None,
            401: inline_serializer("RefreshError", {"detail": serializers.CharField()}),
        },
    )
    def post(self, request):
        raw = request.COOKIES.get(REFRESH_COOKIE)
        try:
            old = RefreshToken(raw)
            user = User.objects.get(pk=old["user_id"], is_active=True)
            old.blacklist()
        except (TokenError, User.DoesNotExist, KeyError):
            return clear_auth_cookies(
                Response({"detail": "Session expired."}, status=status.HTTP_401_UNAUTHORIZED)
            )
        return set_auth_cookies(
            Response(status=status.HTTP_204_NO_CONTENT), RefreshToken.for_user(user)
        )


class LogoutView(CsrfProtectedView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        raw = request.COOKIES.get(REFRESH_COOKIE)
        if raw:
            with contextlib.suppress(TokenError):
                RefreshToken(raw).blacklist()
        return clear_auth_cookies(Response(status=status.HTTP_204_NO_CONTENT))


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)
