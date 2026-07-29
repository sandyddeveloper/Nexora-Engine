"""URL pattern routing for accounts app."""

from django.urls import path

from .views import (
    ChangePasswordAPIView,
    ForgotPasswordAPIView,
    LoginAPIView,
    LogoutAPIView,
    RefreshTokenAPIView,
    RegisterAPIView,
    ResendVerificationAPIView,
    ResetPasswordAPIView,
    UserDetailAPIView,
    UserListAPIView,
    VerifyEmailAPIView,
)

app_name = "accounts"

urlpatterns = [
    path("users/", UserListAPIView.as_view(), name="user-list"),
    path("users/<uuid:pk>/", UserDetailAPIView.as_view(), name="user-detail"),
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("refresh/", RefreshTokenAPIView.as_view(), name="token-refresh"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("change-password/", ChangePasswordAPIView.as_view(), name="change-password"),
    path("forgot-password/", ForgotPasswordAPIView.as_view(), name="forgot-password"),
    path("reset-password/", ResetPasswordAPIView.as_view(), name="reset-password"),
    path("verify-email/", VerifyEmailAPIView.as_view(), name="verify-email"),
    path(
        "resend-verification/",
        ResendVerificationAPIView.as_view(),
        name="resend-verification",
    ),
]
