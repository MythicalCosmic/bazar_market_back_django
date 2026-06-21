import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from base.container import container
from base.responses import success, error
from base.ratelimit import ratelimit

from courier.dto.auth import LoginDTO, SessionDTO
from courier.services.v1.auth_service import CourierAuthService


def _session_dto(request, data) -> SessionDTO:
    return SessionDTO(
        ip_address=request.META.get("REMOTE_ADDR", ""),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        device=(data or {}).get("device", ""),
    )


@csrf_exempt
@require_POST
@ratelimit(10, per=60)
def login_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return error("username and password are required", status=422)
    svc = container.resolve(CourierAuthService)
    result = svc.login(LoginDTO(username=username, password=password), _session_dto(request, data))
    return success(data=result, message="Login successful")


@csrf_exempt
@require_POST
@ratelimit(20, per=60)
def refresh_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")
    token = data.get("refreshToken") or data.get("refresh_token")
    if not token:
        return error("refreshToken is required", status=422)
    svc = container.resolve(CourierAuthService)
    return success(data=svc.refresh(token, _session_dto(request, data)))


@csrf_exempt
@require_POST
def logout_view(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not token and request.body:
        try:
            token = (json.loads(request.body) or {}).get("refreshToken", "")
        except (json.JSONDecodeError, ValueError):
            token = ""
    if not token:
        return error("Authorization header required", status=401)
    svc = container.resolve(CourierAuthService)
    return success(data=svc.logout(token), message="Logout successful")
