# Nexora Engine — Database Conventions & Query Optimization

**Version**: 1.0.0  
**Effective Date**: August 1, 2026  

---

## Database Standards

1. **UUID Primary Keys**: Every table uses a UUIDv4 primary key (`id`).
2. **Soft Deletion**: Records default to soft deletion (`deleted_at`). Hard deletion requires explicit `.hard_delete()`.
3. **Atomic Writes**: Service operations containing multiple SQL writes must be decorated with `@transaction.atomic`.
4. **N+1 Query Elimination**: Selectors must pre-fetch related models using `select_related` (ForeignKeys/OneToOne) and `prefetch_related` (ManyToMany/reverse relations).
5. **Index Naming**: All composite indexes in `Meta.indexes` must define explicit names (`name="idx_<table_prefix>_<fields>"`).
