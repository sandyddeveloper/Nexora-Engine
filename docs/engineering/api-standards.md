# Nexora Engine — API Standards & OpenAPI Conventions

**Version**: 1.0.0  
**Effective Date**: August 1, 2026  

---

## Response Envelope Specification

All REST API endpoints in Nexora Engine return standardized JSON payloads formatted via `core.responses`:

```json
{
  "success": true,
  "message": "Resource action message.",
  "data": {},
  "errors": null,
  "pagination": null
}
```

### HTTP Status Code Guidelines

| Code | Status Name | Usage Criteria |
|---|---|---|
| `200` | OK | Successful GET, PATCH, or POST authentication query. |
| `201` | Created | Successful resource registration or creation. |
| `204` | No Content | Successful deletion response (**Must NOT contain a body** per RFC 9110). |
| `400` | Bad Request | Validation error or domain rule rejection. |
| `401` | Unauthorized | Missing or invalid authentication token. |
| `403` | Forbidden | Authenticated caller lacks required role or permission. |
| `404` | Not Found | Resource or object UUID does not exist. |
| `429` | Too Many Requests | Rate throttle threshold exceeded. |
| `500` | Internal Server Error | Sanitized internal application failure. |

---

## OpenAPI Documentation

Every view method **MUST** be documented using DRF Spectacular `@extend_schema`:

```python
@extend_schema(
    tags=["Signup"],
    summary="Register New User",
    request=RegisterSerializer,
    responses={201: UserDetailSerializer},
)
```
