"""URL pattern routing for roles app."""

from django.urls import path

from .views import RoleDetailAPIView, RoleListAPIView

app_name = "roles"

urlpatterns = [
    path("", RoleListAPIView.as_view(), name="role-list"),
    path("<uuid:pk>/", RoleDetailAPIView.as_view(), name="role-detail"),
]
