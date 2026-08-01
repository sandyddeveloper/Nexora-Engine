# Nexora Engine — Code Review Checklist for Engineers & AI Agents

**Version**: 1.0.0  
**Effective Date**: August 1, 2026  

---

## Pre-Merge Quality Checklist

Every Pull Request submitted to `Nexora Engine` must pass this checklist before approval:

- [ ] **Architecture**: Does the code strictly separate Views (thin HTTP), Services (writes), Selectors (reads), and Models?
- [ ] **Base Model Inheritance**: Does every new model inherit from `apps.common.models.BaseModel`?
- [ ] **Soft Delete**: Is soft deletion respected by default querysets?
- [ ] **Atomic Transactions**: Are multi-step database writes wrapped in `@transaction.atomic` in `services.py`?
- [ ] **N+1 Optimization**: Do selectors use `select_related` or `prefetch_related` for related models?
- [ ] **Pagination**: Are list endpoints wrapped in `paginated_response` with bounded page sizes?
- [ ] **Security & RBAC**: Are endpoints protected by `IsAuthenticated` and `HasRolePermission`?
- [ ] **Rate Limiting**: Are public authentication endpoints protected by DRF throttle classes?
- [ ] **Token Replay**: Are single-use tokens verified for `is_used==False` and marked consumed upon use?
- [ ] **Exception Masking**: Does the exception handler sanitize raw `IntegrityError` and stack traces?
- [ ] **Celery Tasks**: Are email dispatches offloaded to Celery tasks with retry policies (`autoretry_for`)?
- [ ] **OpenAPI Spec**: Is every view method decorated with `@extend_schema`?
- [ ] **Testing**: Are unit and integration tests written and passing (`python manage.py test`)?
- [ ] **System Checks**: Does `python manage.py check` report 0 errors?
