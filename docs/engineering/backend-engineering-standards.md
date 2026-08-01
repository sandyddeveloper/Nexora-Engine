# Nexora Engine — Official Backend Engineering Standards & Architecture Guide

**Version**: 1.0.0  
**Effective Date**: August 1, 2026  
**Status**: Official Engineering Specification  
**Author**: Chief Technology Officer & Backend Architecture Board  

---

## Table of Contents
1. [Project Architecture](#1-project-architecture)
2. [Folder Structure Standards](#2-folder-structure-standards)
3. [Model Standards](#3-model-standards)
4. [Service Layer Standards](#4-service-layer-standards)
5. [Selector Layer Standards](#5-selector-layer-standards)
6. [Serializer Standards](#6-serializer-standards)
7. [APIView Standards](#7-apiview-standards)
8. [Permission Standards](#8-permission-standards)
9. [Authentication Standards](#9-authentication-standards)
10. [Database Standards](#10-database-standards)
11. [Redis Standards](#11-redis-standards)
12. [Celery Standards](#12-celery-standards)
13. [API Standards](#13-api-standards)
14. [Security Standards](#14-security-standards)
15. [Logging Standards](#15-logging-standards)
16. [Testing Standards](#16-testing-standards)
17. [Code Quality Standards](#17-code-quality-standards)
18. [Performance Standards](#18-performance-standards)
19. [Git Standards](#19-git-standards)
20. [Definition of Done](#20-definition-of-done)
21. [Engineering Review Checklist](#21-engineering-review-checklist)
22. [Technical Debt Policy](#22-technical-debt-policy)
23. [Future Architecture Roadmap](#23-future-architecture-roadmap)

---

## 1. Project Architecture

Nexora Engine is built on a **Decoupled Service-Selector Clean Architecture** designed to support **10 Million+ users**, multi-tenant enterprise organizations, and high-concurrency workloads.

```
[ HTTP Request ] ──► [ Thin APIView ] ──► [ Serializer (Validate Only) ]
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [ Service Layer ] (Writes)        [ Selector Layer ] (Reads)
            │                                 │
            ├─► [ @transaction.atomic ]       ├─► [ select_related ]
            ├─► [ Celery Task Delay ]         ├─► [ Redis Cache ]
            ▼                                 ▼
    [ Model Manager ]                 [ QuerySet Execution ]
            │                                 │
            └────────────────┬────────────────┘
                             ▼
                    [ PostgreSQL DB ]
```

### Architectural Principles

1. **Strict Layer Separation**:
   - **Views**: Handle HTTP protocol concerns (routing, permissions, throttling, invoking services/selectors, returning standard JSON responses). Views **MUST NOT** contain business logic or raw ORM queries.
   - **Services (`services.py`)**: Handle all state mutations (Create, Update, Soft Delete, Restore, Password Operations, Audit Logging). Writes **MUST** be atomic.
   - **Selectors (`selectors.py`)**: Handle all read operations (QuerySets, filtering, prefetching, Redis caching). Selectors **MUST NOT** mutate database state.
   - **Serializers (`serializers.py`)**: Handle input validation and data transformation. Serializers **MUST NOT** call database save methods or contain business rules.

2. **Dependency Direction**:
   - `apps.<domain>` may depend on `apps.common` and `core`.
   - Domains **MUST NOT** import directly across boundaries in a way that introduces circular dependencies. Use signals or loose foreign keys (`organization_id = UUIDField`).

3. **Forbidden Architectural Practices**:
   - ❌ Executing database queries (`Model.objects.filter(...)`) directly inside API Views or Serializers.
   - ❌ Placing `@transaction.atomic` inside API Views instead of Service functions.
   - ❌ Performing synchronous I/O (sending emails, third-party API calls) inside HTTP request-response cycles.

---

## 2. Folder Structure Standards

Every application module under `apps/` must conform to the following directory layout:

```
apps/<module_name>/
├── __init__.py
├── admin.py            # Django Admin registration and custom ModelAdmins
├── apps.py             # AppConfig defining label and ready() signal imports
├── managers.py         # Custom BaseManager and SoftDeleteManager extensions
├── models.py           # Domain models extending BaseModel with TextChoices
├── permissions.py      # Custom DRF BasePermission authorization classes
├── selectors.py        # Read-only query functions returning QuerySets or objects
├── serializers.py      # DRF Serializers for request validation and response schemas
├── services.py         # Write operations, business logic, and atomic transactions
├── signals.py          # Post-save/pre-save signal handlers
├── tasks.py            # Async Celery background tasks with retry policies
├── urls.py             # App URL routing definitions
├── views.py            # Thin DRF APIViews decorated with @extend_schema
└── tests/              # Comprehensive test package
    ├── __init__.py
    ├── test_models.py
    ├── test_permissions.py
    ├── test_selectors.py
    └── test_services.py
```

### Top-Level Directories

- `core/`: Global infrastructure, custom middleware, exception handlers, response helpers, and base pagination.
- `config/`: Project settings (`settings.py`), root URL routing (`urls.py`), Celery configuration (`celery.py`), WSGI/ASGI handlers.
- `apps/common/`: Shared abstract base models (`BaseModel`), shared querysets (`SoftDeleteQuerySet`), and universal managers.
- `docs/`: Version-controlled engineering specifications and architecture guides.

---

## 3. Model Standards

Every domain model in Nexora Engine **MUST** inherit from `apps.common.models.BaseModel`.

```python
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import BaseModel

class UserStatus(models.TextChoices):
    ACTIVE = "ACTIVE", _("Active")
    INACTIVE = "INACTIVE", _("Inactive")
    LOCKED = "LOCKED", _("Locked")

class User(BaseModel):
    email = models.EmailField(unique=True, db_index=True, help_text=_("Primary email address."))
    status = models.CharField(
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
        db_index=True,
        help_text=_("Account lifecycle status."),
    )

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        indexes = [
            models.Index(fields=["email", "status"], name="idx_user_email_status"),
        ]
```

### Mandatory Model Features

1. **UUID Primary Keys**: `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`.
2. **Soft Delete**: `deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)`. Default manager (`objects`) automatically filters out soft-deleted instances (`deleted_at__isnull=True`).
3. **Audit Timestamps & Fields**: Every model includes `created_at`, `updated_at`, `created_by`, `updated_by`.
4. **TextChoices Enums**: String fields with restricted choices **MUST** use `models.TextChoices` enums. Magic strings are strictly forbidden.
5. **Field Metadata**: Every field **MUST** specify `help_text` and localization wrappers (`_("...")`).
6. **Explicit Indexes & Constraints**: Composite indexes **MUST** be defined in `Meta.indexes` using explicit `name="idx_..."` identifiers.

---

## 4. Service Layer Standards

The Service Layer (`services.py`) is the sole owner of state mutations and business rules.

```python
from django.db import transaction

@transaction.atomic
def create_user(*, email: str, password: str, **extra_fields) -> User:
    """Create a user, trigger default profile signals, and dispatch verification email atomically."""
    user = User.objects.create_user(email=email, password=password, **extra_fields)
    token = generate_email_verification_token(user)
    send_verification_email_task.delay(str(user.id), token)
    return user
```

### Rules for Services

1. **Keyword-Only Arguments**: All service functions **MUST** use keyword-only arguments (`*, email: str, ...`).
2. **Atomic Transactions**: Multi-step write operations **MUST** be decorated with `@transaction.atomic`.
3. **Async Task Offloading**: Email dispatch, audit logging, and external webhooks **MUST** be offloaded to Celery background tasks (`task.delay(...)`).
4. **Type Annotations**: Service parameters and return types **MUST** be explicitly annotated (`-> User`).

---

## 5. Selector Layer Standards

The Selector Layer (`selectors.py`) is the sole owner of read queries and caching logic.

```python
from typing import Optional
from django.db.models import QuerySet

def get_user(*, user_id: str | uuid.UUID) -> Optional[User]:
    """Retrieve user with pre-fetched profile and preference to prevent N+1 queries."""
    try:
        return User.objects.select_related("profile", "preference").get(pk=user_id)
    except (User.DoesNotExist, ValueError):
        return None

def list_users() -> QuerySet[User]:
    """Return active non-deleted users ordered by creation date descending."""
    return User.objects.select_related("profile", "preference").active().order_by("-created_at")
```

### Performance Rules for Selectors

1. **N+1 Query Elimination**: Selectors **MUST** use `select_related` for 1:1 and ForeignKey relations, and `prefetch_related` for M2M and reverse relations.
2. **No Side Effects**: Selectors **MUST NOT** execute `.save()`, `.update()`, or `.delete()`.

---

## 6. Serializer Standards

Serializers (`serializers.py`) are strictly responsible for data validation and representation.

```python
from rest_framework import serializers

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value.strip()).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return value.lower().strip()
```

### Serializer Constraints

1. **No Save/Update Overrides**: Serializers **MUST NOT** override `create()` or `update()` to perform direct DB writes. Views pass validated serializer data to the Service Layer instead.
2. **Explicit Fields**: `ModelSerializer` classes **MUST** explicitly define `fields = [...]`. Using `fields = "__all__"` is strictly prohibited.

---

## 7. APIView Standards

APIViews (`views.py`) are thin HTTP controller wrappers.

```python
class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(
        tags=["Signin / Login"],
        summary="Authenticate User",
        request=LoginSerializer,
        responses={200: OpenApiResponse(description="Login successful.")},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, reason = services.authenticate_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        if user is None:
            return unauthorized_response(message="Invalid credentials.")
        data = services.build_login_response(user=user)
        return success_response(message="Login successful.", data=data)
```

### Standards for Views

1. **Thin Controller Design**: Views only handle serializer validation, service/selector invocation, and DRF Response rendering.
2. **OpenAPI Decorators**: Every view method **MUST** be decorated with `@extend_schema(...)` containing `tags`, `summary`, and `responses`.
3. **Response Helpers**: Views **MUST** return responses using standardized response helpers from `core.responses`.

---

## 8. Permission Standards

Authorization is enforced using granular DRF `BasePermission` classes.

```python
from rest_framework import permissions

class HasRolePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False
        return bool(user.is_staff or user.is_superuser)
```

1. **Default Deny**: All administrative and data-modifying endpoints **MUST** default to `permission_classes = [IsAuthenticated, HasRolePermission]`.
2. **Public Endpoints**: Only registration, login, token refresh, and health checks are permitted to use `AllowAny`.

---

## 9. Authentication Standards

Authentication uses **SimpleJWT** with refresh token rotation and stateful token blacklisting.

1. **Refresh Token Rotation**: `SIMPLE_JWT = {"ROTATE_REFRESH_TOKENS": True, "BLACKLIST_AFTER_ROTATION": True}`.
2. **Replay Protection**: Single-use tokens (password reset, email verification) **MUST** check `is_used=False` in database records and mark `is_used=True`, `used_at=now` upon consumption.
3. **Device Session Revocation**: Logging out invalidates both the JWT refresh token and marks the associated `UserSession` as `REVOKED`.

---

## 10. Database Standards

1. **Migration Isolation**: Never edit existing, applied migration files. Always generate new incremental migration files (`python manage.py makemigrations`).
2. **Constraint Naming**: Composite indexes and unique constraints **MUST** use explicit naming (`name="idx_..."`, `name="unique_..."`).
3. **PostgreSQL Specifics**: Use `GenericIPAddressField` for IPs, `JSONField` for unstructured metadata, and native `UUIDField`.

---

## 11. Redis Standards

Redis is used for caching, rate limiting, and Celery message brokering.

1. **Key Naming Convention**: `nexora:<module>:<entity>:<identifier>` (e.g. `nexora:accounts:user:uuid123`).
2. **TTL Requirement**: All cached entries **MUST** define an explicit Time-To-Live (TTL) expiration.
3. **Cache Invalidation**: Service mutation functions **MUST** invalidate relevant Redis cache keys upon record update or soft deletion.

---

## 12. Celery Standards

1. **Task Naming**: `apps.<module>.tasks.<task_function_name>` (e.g. `apps.accounts.tasks.send_verification_email_task`).
2. **Retry & Backoff**: All network/I/O tasks **MUST** define retry policies:
   ```python
   @shared_task(
       name="apps.accounts.tasks.send_verification_email_task",
       autoretry_for=(Exception,),
       retry_backoff=True,
       retry_kwargs={"max_retries": 5},
       time_limit=30,
   )
   ```
3. **Idempotency**: Tasks **MUST** be idempotent so re-executing a task produces identical system states.

---

## 13. API Standards

All API responses **MUST** adhere to the standard JSON payload structure:

```json
{
  "success": true,
  "message": "Users retrieved successfully.",
  "data": [ ... ],
  "errors": null,
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_records": 150,
    "total_pages": 8,
    "next": true,
    "previous": false
  }
}
```

### HTTP Status Code Conventions

- `200 OK`: Standard read/update response.
- `201 Created`: Resource creation response.
- `204 No Content`: Successful deletion response (**MUST NOT** contain a response body per RFC 9110).
- `400 Bad Request`: Validation failure or business rule rejection.
- `401 Unauthorized`: Authentication missing or invalid.
- `403 Forbidden`: Authenticated user lacks required permission/role.
- `404 Not Found`: Resource does not exist.
- `429 Too Many Requests`: Rate limit threshold exceeded.
- `500 Internal Server Error`: Masked server error.

---

## 14. Security Standards (OWASP Compliance)

1. **Exception Sanitization**: Raw SQL error messages (`IntegrityError`) and Python stack trace strings **MUST NEVER** be returned to clients in response payloads. `custom_exception_handler` sanitizes errors into generic messages.
2. **Correlation ID Propagation**: `CorrelationIdMiddleware` attaches `X-Request-ID` to all HTTP request contexts and outgoing headers.
3. **Throttling**: Public endpoints **MUST** enforce DRF throttle classes (`LoginRateThrottle`: 5/min, `AuthRateThrottle`: 10/min).

---

## 15. Logging Standards

Loggers are instantiated per domain namespace (`logging.getLogger("nexora.<module>")`).

1. **Log Levels**:
   - `DEBUG`: Verbose query/development info.
   - `INFO`: Audit events, account lifecycle changes, service actions.
   - `WARNING`: Failed login attempts, invalid refresh tokens, permission denials.
   - `ERROR`: System failures, database errors, Celery task exceptions.
2. **Sensitive Data Masking**: Loggers **MUST NEVER** record raw passwords, secret tokens, or full credit card details.

---

## 16. Testing Standards

The test suite is placed under `apps/<module>/tests/`.

```bash
# Execute full test suite
python manage.py test apps.accounts apps.roles tests
```

### Test Requirements

1. **Model Tests**: Test field defaults, custom manager querysets, soft deletion, and string representations.
2. **Service Tests**: Test business operations, atomic rollbacks, and signals.
3. **Selector Tests**: Test filtering, prefetching, and null lookups.
4. **Security & Permission Tests**: Test unauthenticated rejection (401), non-admin rejection (403), token replay prevention, and rate-limiting throttles.

---

## 17. Code Quality Standards

1. **PEP8 Compliance**: All Python code formatted according to PEP8 guidelines using `ruff` / `black`.
2. **Type Hints**: All function signatures in `services.py` and `selectors.py` **MUST** include complete type annotations.
3. **Docstrings**: All classes and functions **MUST** contain Google-style docstrings.
4. **Size Limits**:
   - Maximum module size: 500 lines.
   - Maximum function length: 50 lines.

---

## 18. Performance Standards

1. **Query Count Budget**: Single GET API requests **MUST NOT** exceed 5 database queries.
2. **Latency Target**: 95th percentile response time (p95) **MUST** be under 200ms.
3. **Pagination Enforcement**: All list queries **MUST** enforce pagination (`page_size` max 100). Unpaginated `Model.objects.all()` views are strictly forbidden.

---

## 19. Git Standards

1. **Branch Naming**:
   - Features: `feature/<module>-<short-description>`
   - Bugfixes: `fix/<module>-<short-description>`
2. **Commit Messages**: Follow Conventional Commits format (`feat(accounts): add device tracking service`).
3. **Pull Request Rules**: Every PR requires 2 approving reviews and 100% automated test pass before merging into `main`.

---

## 20. Definition of Done (DoD)

A backend feature is considered **Done** only when:

- [ ] Architecture matches Clean Architecture layering (Views -> Services/Selectors -> Models).
- [ ] Models inherit from `BaseModel` with UUIDs, soft delete, and composite indexes.
- [ ] Services use `@transaction.atomic` for multi-write operations.
- [ ] Selectors use `select_related` / `prefetch_related` and eliminate N+1 queries.
- [ ] Public endpoints have DRF rate throttles attached.
- [ ] Views are decorated with OpenAPI `@extend_schema` tags.
- [ ] Unit & Security integration tests written and passing.
- [ ] System checks pass (`python manage.py check`) with 0 errors.

---

## 21. Engineering Review Checklist

Reviewers and AI agents **MUST** verify this checklist before approving any Pull Request:

```markdown
- [ ] Does every model inherit from BaseModel?
- [ ] Are list endpoints paginated with bounded page sizes?
- [ ] Are writes wrapped inside @transaction.atomic in services.py?
- [ ] Are query selectors optimized with select_related / prefetch_related?
- [ ] Are permissions enforced with HasRolePermission or IsAuthenticated?
- [ ] Is raw SQL / IntegrityError string sanitized in custom_exception_handler?
- [ ] Are single-use tokens verified for is_used==False and marked as used?
- [ ] Are background I/O tasks offloaded to Celery with exponential backoff?
```

---

## 22. Technical Debt Policy

1. **Zero High-Severity Security Debt**: Security vulnerabilities, broken access control, or raw SQL exception leakage **MUST** be fixed immediately.
2. **Mandatory Refactoring Triggers**: Any file exceeding 500 lines or function exceeding 50 lines must be refactored during the next sprint.

---

## 23. Future Architecture Roadmap

As Nexora Engine expands to Phase 3 and beyond (Organization, HRMS, Payroll, CRM, Finance modules):

1. **Multi-Tenancy Isolation**: `Organization` tenant ID scoping will be enforced at the `BaseModel` layer.
2. **Event-Driven Architecture**: Integration events across domains will transition to Celery Event Bus messaging.
3. **CQRS Read Replicas**: Selectors will route read queries to PostgreSQL read-replicas under high concurrent traffic workloads.
