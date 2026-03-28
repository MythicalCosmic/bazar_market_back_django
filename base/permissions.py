import logging
from functools import wraps

from django.core.cache import cache

from base.exceptions import AuthenticationError, ForbiddenError

logger = logging.getLogger(__name__)

CACHE_PREFIX = "perms:"
CACHE_TTL = 300


class P:
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    MANAGE_CATEGORIES = "manage_categories"
    MANAGE_PRODUCTS = "manage_products"
    MANAGE_BANNERS = "manage_banners"
    MANAGE_COUPONS = "manage_coupons"
    MANAGE_DISCOUNTS = "manage_discounts"
    MANAGE_DELIVERY_ZONES = "manage_delivery_zones"
    MANAGE_SETTINGS = "manage_settings"
    MANAGE_ORDERS = "manage_orders"
    MANAGE_PAYMENTS = "manage_payments"
    MANAGE_NOTIFICATIONS = "manage_notifications"
    MANAGE_ANALYTICS = "manage_analytics"

    VIEW_USERS = "view_users"
    VIEW_CATEGORIES = "view_categories"
    VIEW_PRODUCTS = "view_products"
    VIEW_ORDERS = "view_orders"
    VIEW_PAYMENTS = "view_payments"
    VIEW_ANALYTICS = "view_analytics"
    VIEW_DELIVERY_ZONES = "view_delivery_zones"

    ASSIGN_ORDERS = "assign_orders"
    UPDATE_ORDER_STATUS = "update_order_status"
    VIEW_ASSIGNED_ORDERS = "view_assigned_orders"


ALL_PERMISSIONS = {
    v for k, v in vars(P).items() if not k.startswith("_")
}

DEFAULT_ROLE_PERMISSIONS = {
    "admin": ALL_PERMISSIONS,

    "manager": {
        P.MANAGE_CATEGORIES, P.MANAGE_PRODUCTS, P.MANAGE_BANNERS,
        P.MANAGE_COUPONS, P.MANAGE_DISCOUNTS, P.MANAGE_ORDERS,
        P.MANAGE_NOTIFICATIONS, P.MANAGE_DELIVERY_ZONES,
        P.VIEW_USERS, P.VIEW_CATEGORIES, P.VIEW_PRODUCTS,
        P.VIEW_ORDERS, P.VIEW_PAYMENTS, P.VIEW_ANALYTICS,
        P.VIEW_DELIVERY_ZONES, P.ASSIGN_ORDERS, P.UPDATE_ORDER_STATUS,
    },

    "courier": {
        P.VIEW_ASSIGNED_ORDERS, P.UPDATE_ORDER_STATUS, P.VIEW_DELIVERY_ZONES,
    },

    "client": set(),
}


def _cache_safe(fn, *args, default=None):
    try:
        return fn(*args)
    except Exception:
        logger.warning("Redis unavailable, skipping permission cache")
        return default


def _cache_key_role(role: str) -> str:
    return f"{CACHE_PREFIX}role:{role}"


def _cache_key_user(user_id: int) -> str:
    return f"{CACHE_PREFIX}user:{user_id}"


def _get_role_permissions(role: str) -> set:
    cached = _cache_safe(cache.get, _cache_key_role(role))
    if cached is not None:
        return cached

    from base.models import RolePermission
    perms = set(
        RolePermission.objects.filter(role=role)
        .values_list("permission__codename", flat=True)
    )
    _cache_safe(cache.set, _cache_key_role(role), perms, CACHE_TTL)
    return perms


def _get_user_overrides(user_id: int) -> dict:
    cached = _cache_safe(cache.get, _cache_key_user(user_id))
    if cached is not None:
        return cached

    from base.models import UserPermission
    overrides = {}
    for codename, is_granted in (
        UserPermission.objects.filter(user_id=user_id)
        .values_list("permission__codename", "is_granted")
    ):
        overrides[codename] = is_granted
    _cache_safe(cache.set, _cache_key_user(user_id), overrides, CACHE_TTL)
    return overrides


def get_permissions(user) -> set:
    role_perms = _get_role_permissions(user.role)
    overrides = _get_user_overrides(user.id)
    result = set(role_perms)
    for codename, is_granted in overrides.items():
        if is_granted:
            result.add(codename)
        else:
            result.discard(codename)
    return result


def has_permission(user, permission: str) -> bool:
    return permission in get_permissions(user)


def has_any_permission(user, *permissions: str) -> bool:
    user_perms = get_permissions(user)
    return any(p in user_perms for p in permissions)


def has_all_permissions(user, *permissions: str) -> bool:
    user_perms = get_permissions(user)
    return all(p in user_perms for p in permissions)


def clear_permission_cache(role: str = None, user_id: int = None):
    if role:
        _cache_safe(cache.delete, _cache_key_role(role))
    if user_id:
        _cache_safe(cache.delete, _cache_key_user(user_id))


def clear_all_permission_cache():
    from base.models import User
    for role_val, _ in User.Role.choices:
        _cache_safe(cache.delete, _cache_key_role(role_val))


def get_session_from_request(request):
    from base.container import container
    from base.repositories.session import SessionRepository

    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        raise AuthenticationError("Authorization header required")
    token = auth_header[7:]
    session_repo = container.resolve(SessionRepository)
    session = session_repo.get_by_key(token)
    if not session:
        raise AuthenticationError("Invalid or expired session")
    return session


def require_auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        session = get_session_from_request(request)
        request.session_obj = session
        request.user_obj = session.user
        return view_func(request, *args, **kwargs)
    return wrapper


def require_permission(*permissions, match_all=False):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            session = get_session_from_request(request)
            request.session_obj = session
            request.user_obj = session.user
            check = has_all_permissions if match_all else has_any_permission
            if not check(session.user, *permissions):
                raise ForbiddenError("You do not have permission to perform this action")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_role(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            session = get_session_from_request(request)
            request.session_obj = session
            request.user_obj = session.user
            if session.user.role not in roles:
                raise ForbiddenError("Your role does not have access to this resource")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
