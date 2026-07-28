"""Pagination helpers for API-style responses."""

from django.core.paginator import Paginator

from core.responses import list_response


def paginate_queryset(queryset, page_size=20, page=1):
    """Return a paginated page object for the supplied queryset."""
    page_size = min(max(int(page_size), 1), 100)
    page = max(int(page), 1)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    return {
        "data": list(page_obj.object_list),
        "pagination": {
            "page": page_obj.number,
            "page_size": page_size,
            "total_records": paginator.count,
            "total_pages": paginator.num_pages,
            "next": page_obj.has_next(),
            "previous": page_obj.has_previous(),
        },
    }


def paginated_response(
    queryset, message="Data retrieved successfully.", page_size=20, page=1
):
    """Build a DRF response payload with standard pagination metadata."""
    result = paginate_queryset(queryset, page_size=page_size, page=page)
    return list_response(
        result["data"],
        message=message,
        page=result["pagination"]["page"],
        page_size=result["pagination"]["page_size"],
        total_records=result["pagination"]["total_records"],
        total_pages=result["pagination"]["total_pages"],
        next=result["pagination"]["next"],
        previous=result["pagination"]["previous"],
    )
