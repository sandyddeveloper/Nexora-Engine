"""Views for the roles app."""

from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from core.responses import (
    created_response,
    deleted_response,
    not_found_response,
    success_response,
    updated_response,
    validation_error_response,
)

from . import selectors, services
from .serializers import (
    RoleCreateSerializer,
    RoleDetailSerializer,
    RoleSerializer,
    RoleUpdateSerializer,
)


@extend_schema_view(
    get=extend_schema(
        tags=["Roles"],
        summary="List Roles",
        description="Retrieve a paginated list of all roles in the system.",
        responses={200: RoleSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Roles"],
        summary="Create Role",
        description="Create a new role with a unique code.",
        request=RoleCreateSerializer,
        responses={
            201: RoleDetailSerializer,
            400: OpenApiResponse(
                description="Validation error (duplicate code, missing fields)."
            ),
        },
    ),
)
class RoleListAPIView(APIView):
    """List all roles or create a new role."""

    permission_classes = [AllowAny]

    def get(self, request):
        roles = selectors.list_roles()
        return success_response(
            message="Roles retrieved successfully.",
            data=RoleSerializer(roles, many=True).data,
        )

    def post(self, request):
        serializer = RoleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role = services.create_role(
            name=serializer.validated_data["name"],
            code=serializer.validated_data["code"],
            description=serializer.validated_data.get("description", ""),
            is_system=serializer.validated_data.get("is_system", False),
        )

        return created_response(
            message="Role created successfully.",
            data=RoleDetailSerializer(role).data,
        )


@extend_schema_view(
    get=extend_schema(
        tags=["Roles"],
        summary="Retrieve Role Details",
        description="Retrieve detailed information for a specific role by UUID.",
        responses={
            200: RoleDetailSerializer,
            404: OpenApiResponse(description="Role not found."),
        },
    ),
    patch=extend_schema(
        tags=["Roles"],
        summary="Update Role",
        description="Partially update a role's name, description, or active status.",
        request=RoleUpdateSerializer,
        responses={
            200: RoleDetailSerializer,
            400: OpenApiResponse(description="Validation error."),
            404: OpenApiResponse(description="Role not found."),
        },
    ),
    delete=extend_schema(
        tags=["Roles"],
        summary="Delete Role",
        description="Delete a role. System roles cannot be deleted.",
        responses={
            204: OpenApiResponse(description="Role deleted successfully."),
            400: OpenApiResponse(description="System roles cannot be deleted."),
            404: OpenApiResponse(description="Role not found."),
        },
    ),
)
class RoleDetailAPIView(APIView):
    """Retrieve, update, or delete a specific role."""

    permission_classes = [AllowAny]

    def get(self, request, pk):
        role = selectors.get_role(role_id=pk)
        if role is None:
            return not_found_response(message="Role not found.")
        return success_response(
            message="Role retrieved successfully.",
            data=RoleDetailSerializer(role).data,
        )

    def patch(self, request, pk):
        role = selectors.get_role(role_id=pk)
        if role is None:
            return not_found_response(message="Role not found.")

        serializer = RoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role = services.update_role(role=role, **serializer.validated_data)
        return updated_response(
            message="Role updated successfully.",
            data=RoleDetailSerializer(role).data,
        )

    def delete(self, request, pk):
        role = selectors.get_role(role_id=pk)
        if role is None:
            return not_found_response(message="Role not found.")

        success = services.delete_role(role=role)
        if not success:
            return validation_error_response(
                errors={"role": "System roles cannot be deleted."},
                message="Role deletion failed.",
            )

        return deleted_response(message="Role deleted successfully.")
