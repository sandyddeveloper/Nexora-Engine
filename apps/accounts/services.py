"""Service methods for managing users in the accounts app."""

import logging

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

logger = logging.getLogger("nexora.auth")


def create_user(
    *, email: str, password: str, is_email_verified: bool = True, **extra_fields
) -> User:
    """Create and return a new User using the custom manager."""
    user = User.objects.create_user(
        email=email,
        password=password,
        is_email_verified=is_email_verified,
        **extra_fields,
    )
    if not is_email_verified:
        token = generate_email_verification_token(user)
        logger.info("Verification token generated for new user %s: %s", email, token)
        verification_url = f"/verify-email/?token={token}"
        print(
            f"[VERIFICATION LINK LOG] Verification link for {email}: {verification_url}"
        )
    return user


def update_user(*, user: User, **fields) -> User:
    """Update fields on an existing User instance."""
    allowed_fields = {"first_name", "last_name", "username", "is_active", "is_staff"}
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(user, field, value)
    user.save()
    return user


def activate_user(*, user: User) -> User:
    """Activate a user account."""
    user.is_active = True
    user.save(update_fields=["is_active", "updated_at"])
    return user


def deactivate_user(*, user: User) -> User:
    """Deactivate a user account."""
    user.is_active = False
    user.save(update_fields=["is_active", "updated_at"])
    return user


def change_password(*, user: User, new_password: str) -> User:
    """Change a user's password."""
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    return user


# ── Authentication Services ──────────────────────────────────


def authenticate_user(*, email: str, password: str):
    """Authenticate a user with email and password.

    Returns (user, reason) tuple. Reason will be one of:
    - 'SUCCESS': User authenticated and email verified
    - 'UNVERIFIED_EMAIL': Credentials valid but email is not verified
    - 'INACTIVE_ACCOUNT': User exists but is deactivated
    - 'INVALID_CREDENTIALS': Invalid email or password
    """
    user = authenticate(email=email, password=password)
    if user is None:
        logger.warning("Failed login attempt for email: %s", email)
        return None, "INVALID_CREDENTIALS"
    if not user.is_active:
        logger.warning("Login attempt for inactive account: %s", email)
        return None, "INACTIVE_ACCOUNT"
    if not user.is_email_verified:
        logger.warning("Login attempt for unverified account: %s", email)
        return None, "UNVERIFIED_EMAIL"
    return user, "SUCCESS"


def generate_tokens(*, user) -> dict:
    """Generate JWT access and refresh tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def build_login_response(*, user) -> dict:
    """Build the complete login response data payload.

    Combines JWT tokens with a safe user profile representation.
    Also updates the user's last_login timestamp.
    """
    tokens = generate_tokens(user=user)

    # Update last_login
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])

    return {
        **tokens,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
    }


def refresh_access_token(*, refresh_token: str) -> dict | None:
    """Validate a refresh token and return new access + refresh tokens.

    Returns None if the token is invalid, expired, or blacklisted.
    When rotation is enabled, the old refresh token is blacklisted
    and a new refresh token is issued.
    """
    try:
        from django.conf import settings

        jwt_settings = getattr(settings, "SIMPLE_JWT", {})
        refresh = RefreshToken(refresh_token)

        if jwt_settings.get("ROTATE_REFRESH_TOKENS", False):
            if jwt_settings.get("BLACKLIST_AFTER_ROTATION", False):
                refresh.blacklist()
            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()

        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
        return data
    except Exception:
        logger.warning("Invalid or expired refresh token used")
        return None


def logout_user(*, refresh_token: str) -> bool:
    """Blacklist a refresh token to invalidate the session.

    Returns True on success, False if the token is invalid.
    """
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        logger.info("User logged out, refresh token blacklisted")
        return True
    except Exception:
        logger.warning("Logout failed: invalid or already blacklisted token")
        return False


# ── Password Management Services ──────────────────────────────


def generate_reset_token(user: User) -> str:
    """Generate a combined base64(uid).token string for password reset."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f"{uidb64}.{token}"


def verify_and_get_user_from_token(token_str: str) -> User | None:
    """Verify reset token and return user, or None if invalid/expired/reused."""
    try:
        if "." not in token_str:
            return None
        uidb64, token = token_str.split(".", 1)
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        if not user.is_active:
            return None
        if not default_token_generator.check_token(user, token):
            return None
        return user
    except Exception:
        return None


def change_user_password(
    *, user: User, current_password: str, new_password: str
) -> bool:
    """Change user password after verifying current_password.

    Returns True on success, False if current_password is wrong.
    """
    if not user.check_password(current_password):
        logger.warning(
            "Password change failed for user %s: wrong current_password", user.email
        )
        return False

    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    logger.info("Password changed successfully for user %s", user.email)
    return True


def request_password_reset(*, email: str) -> None:
    """Request a password reset token for the given email.

    Always executes safely without exposing whether the email exists.
    """
    try:
        user = User.objects.get(email=email, is_active=True)
        token = generate_reset_token(user)
        logger.info("Password reset token generated for user %s: %s", email, token)
    except User.DoesNotExist:
        logger.info(
            "Password reset requested for non-existent/inactive email: %s", email
        )


def reset_password_with_token(*, token: str, new_password: str) -> bool:
    """Reset user password using a valid one-time reset token.

    Returns True on success, False if token is invalid, expired, or reused.
    """
    user = verify_and_get_user_from_token(token)
    if user is None:
        logger.warning("Invalid or expired password reset token used")
        return False

    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    logger.info("Password reset successfully for user %s", user.email)
    return True


# ── Email Verification Services ──────────────────────────────

email_signer = TimestampSigner(salt="nexora.email_verification")


def generate_email_verification_token(user: User) -> str:
    """Generate a signed base64(uid).signature email verification token."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    signed_value = email_signer.sign(str(user.pk))
    return f"{uidb64}.{signed_value}"


def verify_email(*, token: str, max_age: int = 86400) -> tuple[bool, str]:
    """Verify user email using signed verification token.

    Token expires after max_age seconds (default: 24 hours / 86400s).
    Returns (success: bool, message/reason: str).
    """
    try:
        if "." not in token:
            return False, "Invalid verification token."
        uidb64, signed_value = token.split(".", 1)
        uid = force_str(urlsafe_base64_decode(uidb64))

        user = User.objects.get(pk=uid)
        if user.is_email_verified:
            return False, "Email address is already verified."

        try:
            unsigned_pk = email_signer.unsign(signed_value, max_age=max_age)
            if unsigned_pk != str(user.pk):
                return False, "Invalid verification token."
        except SignatureExpired:
            return False, "Verification token has expired."
        except BadSignature:
            return False, "Invalid verification token."

        user.is_email_verified = True
        user.email_verified_at = timezone.now()
        user.save(
            update_fields=["is_email_verified", "email_verified_at", "updated_at"]
        )
        logger.info("Email verified successfully for user %s", user.email)
        return True, "Email verified successfully."
    except Exception:
        return False, "Invalid verification token."


def resend_verification_email(*, email: str) -> None:
    """Resend email verification token for the given email.

    Always executes safely without exposing whether the email exists.
    """
    try:
        user = User.objects.get(email=email, is_active=True)
        if not user.is_email_verified:
            token = generate_email_verification_token(user)
            logger.info("Verification token resent for user %s: %s", email, token)
            verification_url = f"/verify-email/?token={token}"
            print(
                "[VERIFICATION LINK LOG] Resent verification link for "
                f"{email}: {verification_url}"
            )
        else:
            logger.info(
                "Resend verification requested for already verified email: %s", email
            )
    except User.DoesNotExist:
        logger.info(
            "Resend verification requested for non-existent/inactive email: %s", email
        )
