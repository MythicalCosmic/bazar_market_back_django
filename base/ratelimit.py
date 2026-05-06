from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse


def ratelimit(calls, per, key_func=None):
    """
    Atomic fixed-window rate limit using Redis INCR.

    Args:
        calls: Maximum requests per window.
        per: Window size in seconds.
        key_func: Callable(request) -> str. Defaults to client IP from REMOTE_ADDR.
    """
    if key_func is None:
        key_func = _get_client_ip

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            ident = key_func(request)
            cache_key = f"rl:{view_func.__module__}.{view_func.__qualname__}:{ident}"

            try:
                count = cache.incr(cache_key)
            except ValueError:
                cache.set(cache_key, 1, timeout=per)
                count = 1

            if count > calls:
                return JsonResponse(
                    {"success": False, "message": "Too many requests. Please try again later."},
                    status=429,
                    headers={"Retry-After": str(per)},
                )

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def _get_client_ip(request):
    """Return REMOTE_ADDR. Do NOT trust X-Forwarded-For directly — it is client-controllable
    unless terminated by a known proxy. Configure your proxy/loadbalancer to set REMOTE_ADDR
    correctly (or use Django's USE_X_FORWARDED_HOST + a trusted-proxies middleware)."""
    return request.META.get("REMOTE_ADDR", "unknown")
