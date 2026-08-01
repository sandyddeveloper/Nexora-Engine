# Nexora Engine — Security Guidelines & OWASP Compliance

**Version**: 1.0.0  
**Effective Date**: August 1, 2026  

---

## OWASP Top 10 Safeguards

1. **Broken Access Control (A01)**: Every endpoint default-denies unauthenticated traffic. Admin endpoints require `IsAuthenticated` and `HasRolePermission`.
2. **Cryptographic Failures (A02)**: Passwords hashed using PBKDF2 with SHA-256. Single-use tokens hashed via SHA-256 (`token_hash`).
3. **Injection Prevention (A03)**: Parameterized queries used exclusively via Django ORM. Raw SQL queries prohibited.
4. **Insecure Design (A04)**: Stateful token consumption enforcement (`is_used=True`) prevents replay attacks.
5. **Security Misconfiguration (A05)**: `custom_exception_handler` masks database errors (`IntegrityError`) and Python stack trace strings.
6. **Identification and Authentication Failures (A07)**: SimpleJWT refresh token rotation and blacklisting active. Throttles enforce 5 req/min on login endpoints.
7. **Security Logging & Monitoring (A09)**: All authentication attempts logged to `LoginHistory` audit table with client IP, user agent, and timestamp. Correlation IDs (`X-Request-ID`) attached via `CorrelationIdMiddleware`.
