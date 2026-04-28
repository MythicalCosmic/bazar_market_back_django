from src.config.config import API_TOKEN

# Pre-encode once at import time so we don't re-encode on every request.
# Comparing bytes-to-bytes also avoids the gotcha where `b"123" != 123`.
EXPECTED_TOKEN = API_TOKEN.encode() if API_TOKEN else None
HEADER_NAME = b"x-api-token"


class TokenAuthMiddleware:
    """Pure ASGI middleware that validates the X-API-TOKEN header.

    Runs in the ASGI call chain with no extra task or body buffering,
    so it adds essentially zero overhead to upload/download streaming.
    """

    # Paths that should not require an API token (e.g. monitoring probes).
    EXEMPT_PATHS = frozenset({"/health", "/docs", "/openapi.json", "/redoc"})

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Only guard HTTP requests; let websockets and lifespan events through.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope["path"] in self.EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        # scope["headers"] is a list of (name_bytes, value_bytes) tuples,
        # with header names already lowercased by the ASGI server.
        token = None
        for name, value in scope["headers"]:
            if name == HEADER_NAME:
                token = value
                break

        if EXPECTED_TOKEN is None or token != EXPECTED_TOKEN:
            await self._send_unauthorized(send)
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _send_unauthorized(send):
        body = b'{"success":false,"message":"Invalid or missing API Token"}'
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
