"""Views for the accounts app."""

from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from core.pagination import paginated_response
from core.responses import (
    created_response,
    deleted_response,
    not_found_response,
    success_response,
    unauthorized_response,
    updated_response,
    validation_error_response,
)


class LoginRateThrottle(AnonRateThrottle):
    rate = "5/minute"


class AuthRateThrottle(AnonRateThrottle):
    rate = "10/minute"

from . import selectors, services
from .serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    ResetPasswordSerializer,
    TokenRefreshSerializer,
    UserCreateSerializer,
    UserDetailSerializer,
    UserSerializer,
    UserUpdateSerializer,
    VerifyEmailSerializer,
)


@extend_schema_view(
    get=extend_schema(
        tags=["Users"],
        summary="List Users",
        description=(
            "Retrieve a list of all registered users in descending order "
            "of creation date."
        ),
        responses={200: UserSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Users"],
        summary="Create User",
        description=(
            "Create a new user account with email, password, and optional "
            "profile details."
        ),
        request=UserCreateSerializer,
        responses={
            201: UserDetailSerializer,
            400: OpenApiResponse(description="Validation error occurred."),
        },
    ),
)
class UserListAPIView(APIView):
    """API view for listing and creating users."""

    permission_classes = [AllowAny]

    def get(self, request):
        users = selectors.list_users()
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        return paginated_response(
            users,
            serializer_class=UserSerializer,
            message="Users retrieved successfully.",
            page=page,
            page_size=page_size,
        )

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.create_user(**serializer.validated_data)
        return created_response(
            message="User created successfully.",
            data=UserDetailSerializer(user).data,
        )


@extend_schema_view(
    get=extend_schema(
        tags=["Users"],
        summary="Retrieve User Details",
        description=(
            "Retrieve detailed profile information for a specific user " "by UUID."
        ),
        responses={
            200: UserDetailSerializer,
            404: OpenApiResponse(description="User not found."),
        },
    ),
    patch=extend_schema(
        tags=["Users"],
        summary="Update User Profile",
        description=(
            "Partially update profile information (first_name, last_name, "
            "username) for a specific user."
        ),
        request=UserUpdateSerializer,
        responses={
            200: UserDetailSerializer,
            400: OpenApiResponse(description="Validation error occurred."),
            404: OpenApiResponse(description="User not found."),
        },
    ),
    delete=extend_schema(
        tags=["Users"],
        summary="Deactivate User",
        description="Deactivate a user account by setting `is_active=False`.",
        responses={
            204: OpenApiResponse(description="User deactivated successfully."),
            404: OpenApiResponse(description="User not found."),
        },
    ),
)
class UserDetailAPIView(APIView):
    """API view for retrieving, updating, and deactivating a specific user."""

    permission_classes = [AllowAny]

    def get(self, request, pk):
        user = selectors.get_user(user_id=pk)
        if not user:
            return not_found_response(message="User not found.")
        return success_response(
            message="User retrieved successfully.",
            data=UserDetailSerializer(user).data,
        )

    def patch(self, request, pk):
        user = selectors.get_user(user_id=pk)
        if not user:
            return not_found_response(message="User not found.")
        serializer = UserUpdateSerializer(
            instance=user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        updated_user = services.update_user(user=user, **serializer.validated_data)
        return updated_response(
            message="User updated successfully.",
            data=UserDetailSerializer(updated_user).data,
        )

    def delete(self, request, pk):
        user = selectors.get_user(user_id=pk)
        if not user:
            return not_found_response(message="User not found.")
        services.deactivate_user(user=user)
        return deleted_response(message="User deactivated successfully.")


class RegisterAPIView(APIView):
    """Public endpoint for new user registration."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        tags=["Signup"],
        summary="Register a New User",
        description=(
            "Create a new user account. Accepts email, password, "
            "confirm_password, first_name, and last_name. "
            "The password is validated against Django's password validators "
            "and is hashed before storage. Returns the created user profile "
            "without sensitive fields."
        ),
        request=RegisterSerializer,
        responses={
            201: UserDetailSerializer,
            400: OpenApiResponse(
                description=(
                    "Validation error (missing fields, weak password, duplicate "
                    "email, password mismatch)."
                )
            ),
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = services.create_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            first_name=serializer.validated_data["first_name"],
            last_name=serializer.validated_data["last_name"],
            is_email_verified=False,
        )

        return created_response(
            message="User registered successfully.",
            data=UserDetailSerializer(user).data,
        )


class LoginAPIView(APIView):
    """Public endpoint for user login via JWT."""

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(
        tags=["Signin / Login"],
        summary="Login",
        description=(
            "Authenticate a user with email and password. "
            "Returns a JWT access token, a refresh token, and the user profile. "
            "A generic error message is returned for any authentication failure "
            "to avoid leaking whether the email or password was incorrect."
        ),
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                description=(
                    "Login successful. Returns access token, refresh token, "
                    "and user profile."
                )
            ),
            401: OpenApiResponse(
                description="Invalid credentials or inactive account."
            ),
            400: OpenApiResponse(
                description="Validation error (missing or invalid fields)."
            ),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user, reason = services.authenticate_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        if reason == "UNVERIFIED_EMAIL":
            return unauthorized_response(
                message="Please verify your email address before logging in.",
            )

        if user is None:
            return unauthorized_response(
                message="Invalid email or password.",
            )

        data = services.build_login_response(user=user)
        return success_response(message="Login successful.", data=data)


class RefreshTokenAPIView(APIView):
    """Public endpoint for refreshing access (and optionally refresh) tokens."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Tokens"],
        summary="Refresh Access Token",
        description=(
            "Accepts a valid, non-blacklisted refresh token and returns a new "
            "access token. If token rotation is enabled, a new refresh token "
            "will also be returned and the provided refresh token will be blacklisted."
        ),
        request=TokenRefreshSerializer,
        responses={
            200: OpenApiResponse(description="Token refreshed successfully."),
            400: OpenApiResponse(
                description="Invalid, expired, or blacklisted refresh token."
            ),
        },
    )
    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = services.refresh_access_token(
            refresh_token=serializer.validated_data["refresh"]
        )

        if result is None:
            return validation_error_response(
                errors={"refresh": "Invalid, expired, or blacklisted token."},
                message="Token refresh failed.",
            )

        return success_response(
            message="Token refreshed successfully.",
            data=result,
        )


class LogoutAPIView(APIView):
    """Authenticated endpoint to invalidate (blacklist) a refresh token."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Signin / Login"],
        summary="Logout",
        description="Blacklists the provided refresh token, invalidating the session.",
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(description="Logged out successfully."),
            400: OpenApiResponse(description="Invalid or blacklisted refresh token."),
            401: OpenApiResponse(
                description="Authentication credentials were not provided."
            ),
        },
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success = services.logout_user(
            refresh_token=serializer.validated_data["refresh"]
        )

        if not success:
            return validation_error_response(
                errors={"refresh": "Invalid or already blacklisted token."},
                message="Logout failed.",
            )

        return success_response(
            message="Logged out successfully.",
            data=None,
        )


class ChangePasswordAPIView(APIView):
    """Authenticated endpoint to change current password."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Signin / Login"],
        summary="Change Password",
        description=(
            "Allows an authenticated user to change their password by supplying "
            "current and new passwords."
        ),
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully."),
            400: OpenApiResponse(
                description=(
                    "Validation error (wrong current password, password mismatch, "
                    "weak password, same password)."
                )
            ),
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success = services.change_user_password(
            user=request.user,
            current_password=serializer.validated_data["current_password"],
            new_password=serializer.validated_data["new_password"],
        )

        if not success:
            return validation_error_response(
                errors={"current_password": "Current password is incorrect."},
                message="Password change failed.",
            )

        return success_response(
            message="Password changed successfully.",
            data=None,
        )


class ForgotPasswordAPIView(APIView):
    """Public endpoint to request password reset token."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        tags=["Signin / Login"],
        summary="Forgot Password",
        description=(
            "Generates a password reset token if account exists. Always returns "
            "generic success response to prevent email enumeration."
        ),
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(
                description="If an account exists, a password reset link has been sent."
            ),
            400: OpenApiResponse(
                description="Validation error (invalid email format)."
            ),
        },
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        services.request_password_reset(email=serializer.validated_data["email"])

        return success_response(
            message="If an account exists, a password reset link has been sent.",
            data=None,
        )


class ResetPasswordAPIView(APIView):
    """Public endpoint to reset password using token."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        tags=["Signin / Login"],
        summary="Reset Password",
        description="Resets user password using a valid one-time token.",
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successfully."),
            400: OpenApiResponse(
                description="Invalid, expired, or reused token, or weak password."
            ),
        },
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success = services.reset_password_with_token(
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
        )

        if not success:
            return validation_error_response(
                errors={"token": "Invalid, expired, or reused password reset token."},
                message="Password reset failed.",
            )

        return success_response(
            message="Password reset successfully.",
            data=None,
        )


class VerifyEmailAPIView(APIView):
    """Public endpoint to verify user email address using token."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Signup"],
        summary="Verify Email",
        description="Verifies user email address using a valid verification token.",
        request=VerifyEmailSerializer,
        responses={
            200: OpenApiResponse(description="Email verified successfully."),
            400: OpenApiResponse(
                description="Invalid, expired, or already used verification token."
            ),
        },
    )
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success, message = services.verify_email(
            token=serializer.validated_data["token"]
        )

        if not success:
            return validation_error_response(
                errors={"token": message},
                message="Email verification failed.",
            )

        return success_response(
            message="Email verified successfully.",
            data=None,
        )


class ResendVerificationAPIView(APIView):
    """Public endpoint to resend email verification token."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        tags=["Signup"],
        summary="Resend Verification Email",
        description=(
            "Resends verification token if account requires verification. Always "
            "returns generic success response to prevent email enumeration."
        ),
        request=ResendVerificationSerializer,
        responses={
            200: OpenApiResponse(
                description=(
                    "If the account requires verification, a new verification "
                    "email has been sent."
                )
            ),
            400: OpenApiResponse(
                description="Validation error (invalid email format)."
            ),
        },
    )
    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        services.resend_verification_email(email=serializer.validated_data["email"])

        return success_response(
            message=(
                "If the account requires verification, a new verification "
                "email has been sent."
            ),
            data=None,
        )
