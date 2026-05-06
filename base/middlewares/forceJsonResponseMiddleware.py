from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.utils.deprecation import MiddlewareMixin

from base.exceptions import ServiceError, ValidationError


_NON_JSON_PREFIXES = ("/admin/", "/static/", "/media/", "/docs/", "/telescope/")


class JSONResponseMiddleware(MiddlewareMixin):

    def process_exception(self, request, exception):
        if isinstance(exception, ValidationError):
            body = {"success": False, "message": exception.message}
            if exception.errors:
                body["errors"] = exception.errors
            return JsonResponse(body, status=exception.status)

        if isinstance(exception, ServiceError):
            return JsonResponse(
                {"success": False, "message": exception.message},
                status=exception.status,
            )

        import logging
        logging.getLogger(__name__).exception(f"Unhandled exception on {request.path}: {exception}")
        return JsonResponse(
            {"success": False, "message": str(exception) if settings.DEBUG else "Internal server error"},
            status=500,
        )

    def process_response(self, request, response):
        if isinstance(response, (JsonResponse, StreamingHttpResponse)):
            return response
        if response.status_code < 400:
            return response
        # Don't rewrite errors for non-API paths (admin, static, docs, telescope).
        path = request.path or ""
        if any(path.startswith(p) for p in _NON_JSON_PREFIXES):
            return response
        accept = request.META.get("HTTP_ACCEPT", "")
        if "text/html" in accept and "application/json" not in accept:
            return response
        return JsonResponse(
            {"success": False, "message": self._status_message(response.status_code)},
            status=response.status_code,
        )

    @staticmethod
    def _status_message(code):
        messages = {
            400: "Bad request",
            401: "Authentication required",
            403: "Access denied",
            404: "Not found",
            405: "Method not allowed",
            409: "Conflict",
            422: "Validation failed",
            429: "Too many requests",
            500: "Internal server error",
            502: "Bad gateway",
            503: "Service unavailable",
        }
        return messages.get(code, f"Error ({code})")
