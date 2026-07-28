"""Pagination helpers for API-style responses."""

from django.core.paginator import Paginator


def paginate_queryset(queryset, page_size=20, page=1):
    """Return a paginated page object for the supplied queryset."""
    paginator = Paginator(queryset, page_size)
    return paginator.get_page(page)
