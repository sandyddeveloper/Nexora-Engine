"""Custom middleware hooks."""

from django.utils.deprecation import MiddlewareMixin


class RequestLoggingMiddleware(MiddlewareMixin):
    """Placeholder middleware for request-level logging."""

    def process_request(self, request):
        request._start_time = None
        return None
