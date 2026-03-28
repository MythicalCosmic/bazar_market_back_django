import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from base.container import container
from base.responses import success, error
from admins.dto.auth import LoginDTO, SessionDTO
from admins.services.v1.auth_service import AuthService


@csrf_exempt
@require_POST
def login_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return error("Username and password are required", status=422)

    auth_service = container.resolve(AuthService)
    result = auth_service.login(
        LoginDTO(username=username, password=password),
        SessionDTO(
            ip_address=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            device=data.get("device", ""),
        ),
    )
    return success(data=result, message="Login successful")


@csrf_exempt
@require_POST
def logout_view(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        return error("Authorization header required", status=401)

    session_token = auth_header[7:]
    auth_service = container.resolve(AuthService)
    result = auth_service.logout(session_token)
    return success(data=result, message="Logout successful")

@csrf_exempt
@require_POST
def logout_all_view(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        return error("Authorization header required", status=401)
    
    session_token = auth_header[7:]
    auth_service = container.resolve(AuthService)
    result = auth_service.logout_all(session_token)
    return success(data=result, message="Loggout successful for all devices")


@csrf_exempt
@require_GET
def me_view(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        return error("Authorization header required", status=401)
    
    session_token = auth_header[7:]
    auth_service = container.resolve(AuthService)
    result = auth_service.me(session_token)
    return success(data=result, message="Profile retrival successful")