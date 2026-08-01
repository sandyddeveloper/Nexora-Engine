"""Custom middleware hooks for request logging, correlation IDs, and security context."""

import uuid

from django.utils.deprecation import MiddlewareMixin


class CorrelationIdMiddleware(MiddlewareMixin):
    """Attach a unique correlation ID (X-Request-ID) to incoming requests and outgoing response headers."""

    def process_request(self, request):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = request_id

    def process_response(self, request, response):
        if hasattr(request, "request_id"):
            response["X-Request-ID"] = request.request_id
        return response
