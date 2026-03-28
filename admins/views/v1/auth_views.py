import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

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
