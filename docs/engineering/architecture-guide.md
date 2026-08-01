# Nexora Engine — Architecture Guide

**Version**: 1.0.0  
**Effective Date**: August 1, 2026  

---

## Clean Architecture & Domain Isolation

Nexora Engine enforces a decoupled Clean Architecture pattern where each domain module in `apps/` functions as an isolated bounded context.

```
                  +--------------------------+
                  |   Thin API Controllers   |
                  |       (views.py)         |
                  +------------+-------------+
                               |
            +------------------+------------------+
            |                                     |
            v                                     v
+-----------------------+             +-----------------------+
|     Service Layer     |             |    Selector Layer     |
|     (services.py)     |             |    (selectors.py)     |
|   Write Operations    |             |    Read Operations    |
+-----------+-----------+             +-----------+-----------+
            |                                     |
            +------------------+------------------+
                               |
                               v
                  +--------------------------+
                  |      Domain Models       |
                  |       (models.py)        |
                  +--------------------------+
```

### Layer Rules

1. **Views Layer**: Protocol handler. Receives HTTP request, checks permissions/throttling, validates payload via Serializer, delegates write/read to Service/Selector, and returns standard Response envelope.
2. **Service Layer**: State mutation authority. Handles atomic writes, transaction boundaries, password hashing, device registrations, session revocations, and dispatches Celery background tasks.
3. **Selector Layer**: Data retrieval authority. Executes optimized QuerySets using `select_related`, `prefetch_related`, and Redis caching.
4. **Models Layer**: Entity definition. Inherits from `BaseModel` providing UUID primary keys, audit timestamps, soft deletion, and composite indexes.
