from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
import time


def ratelimit(calls, per, key_func=None):
    """
    Rate limiting decorator using Django's cache (Redis).

    Args:
        calls: Maximum number of requests allowed in the window.
        per: Time window in seconds.
        key_func: Callable(request) -> str that returns the rate limit key.
                  Defaults to client IP.
    """
    if key_func is None:
        key_func = _get_client_ip

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            ident = key_func(request)
            cache_key = f"ratelimit:{view_func.__module__}.{view_func.__qualname__}:{ident}"

            now = time.time()
            window_start = now - per

            timestamps = cache.get(cache_key, [])
            timestamps = [t for t in timestamps if t > window_start]

            if len(timestamps) >= calls:
                retry_after = int(per - (now - timestamps[0])) + 1
                return JsonResponse(
                    {"success": False, "message": "Too many requests. Please try again later."},
                    status=429,
                    headers={"Retry-After": str(retry_after)},
                )

            timestamps.append(now)
            cache.set(cache_key, timestamps, timeout=per)
            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def _get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")
