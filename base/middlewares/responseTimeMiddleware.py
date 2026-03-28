import json
import time

from django.utils.deprecation import MiddlewareMixin


class ResponseTimeMiddleware(MiddlewareMixin):

    def process_request(self, request):
        request._response_start = time.monotonic()

    def process_response(self, request, response):
        if not hasattr(request, "_response_start"):
            return response
        elapsed_ms = round((time.monotonic() - request._response_start) * 1000, 2)
        if "application/json" in response.get("Content-Type", ""):
            try:
                data = json.loads(response.content)
                data["responseMS"] = elapsed_ms
                response.content = json.dumps(data).encode("utf-8")
            except (json.JSONDecodeError, ValueError):
                pass
        return response
