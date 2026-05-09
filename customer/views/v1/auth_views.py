import json
from dataclasses import fields

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET, require_http_methods

from base.container import container
from base.responses import success, error, created
from base.permissions import require_auth
from base.ratelimit import ratelimit
from customer.dto.auth import RegisterDTO, SessionDTO
from customer.dto.profile import UpdateProfileDTO
from customer.services.v1.auth_service import CustomerAuthService


_PROFILE_FIELDS = {f.name for f in fields(UpdateProfileDTO)}


@csrf_exempt
@require_POST
@ratelimit(3, per=60)
def register_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    required = ["phone", "first_name"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}", status=422)

    dto = RegisterDTO(
        phone=data["phone"],
        first_name=data["first_name"],
        last_name=data.get("last_name", ""),
        language=data.get("language", "uz"),
        telegram_id=data.get("telegram_id"),
    )

    svc = container.resolve(CustomerAuthService)
    result = svc.register(dto)
    return success(data=result, message="Verification code sent")


@csrf_exempt
@require_POST
@ratelimit(5, per=60)
def verify_register_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    phone = data.get("phone")
    code = data.get("code")
    if not phone or not code:
        return error("phone and code are required", status=422)

    svc = container.resolve(CustomerAuthService)
    result = svc.verify_register(
        phone=phone,
        code=str(code),
        session_info=SessionDTO(
            ip_address=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            device=data.get("device", ""),
        ),
    )
    return created(data=result, message="Registration successful")


@csrf_exempt
@require_POST
@ratelimit(1, per=60)
def resend_register_code_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    phone = data.get("phone")
    if not phone:
        return error("phone is required", status=422)

    svc = container.resolve(CustomerAuthService)
    result = svc.resend_register_code(phone)
    return success(data=result)


@csrf_exempt
@require_POST
@ratelimit(3, per=60)
def login_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    phone = data.get("phone")
    if not phone:
        return error("phone is required", status=422)

    svc = container.resolve(CustomerAuthService)
    result = svc.login(phone)
    return success(data=result, message="Verification code sent")


@csrf_exempt
@require_POST
@ratelimit(5, per=60)
def verify_login_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    phone = data.get("phone")
    code = data.get("code")
    if not phone or not code:
        return error("phone and code are required", status=422)

    svc = container.resolve(CustomerAuthService)
    result = svc.verify_login(
        phone=phone,
        code=str(code),
        session_info=SessionDTO(
            ip_address=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            device=data.get("device", ""),
        ),
    )
    return success(data=result, message="Login successful")


@csrf_exempt
@require_POST
@ratelimit(1, per=60)
def resend_login_code_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    phone = data.get("phone")
    if not phone:
        return error("phone is required", status=422)

    svc = container.resolve(CustomerAuthService)
    result = svc.resend_login_code(phone)
    return success(data=result)


@csrf_exempt
@require_POST
@require_auth
def logout_view(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    token = auth_header[7:]
    svc = container.resolve(CustomerAuthService)
    return success(data=svc.logout(token))


@csrf_exempt
@require_POST
@require_auth
def logout_all_view(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    token = auth_header[7:]
    svc = container.resolve(CustomerAuthService)
    return success(data=svc.logout_all(token))


@csrf_exempt
@require_GET
@require_auth
def me_view(request):
    svc = container.resolve(CustomerAuthService)
    return success(data=svc.get_profile(request.user_obj))


@csrf_exempt
@require_http_methods(["PATCH"])
@require_auth
def update_profile_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    dto = UpdateProfileDTO(**{k: v for k, v in data.items() if k in _PROFILE_FIELDS})
    svc = container.resolve(CustomerAuthService)
    result = svc.update_profile(request.user_obj, dto)
    return success(data=result, message="Profile updated")


@csrf_exempt
@require_POST
@require_auth
@ratelimit(3, per=60)
def request_phone_change_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    new_phone = data.get("new_phone")
    if not new_phone:
        return error("new_phone is required", status=422)

    svc = container.resolve(CustomerAuthService)
    result = svc.request_phone_change(request.user_obj, new_phone)
    return success(data=result)


@csrf_exempt
@require_POST
@require_auth
@ratelimit(5, per=60)
def verify_phone_change_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    code = data.get("code")
    if not code:
        return error("code is required", status=422)

    svc = container.resolve(CustomerAuthService)
    result = svc.verify_phone_change(request.user_obj, str(code))
    return success(data=result, message="Phone number updated")


@csrf_exempt
@require_POST
@require_auth
def delete_account_view(request):
    svc = container.resolve(CustomerAuthService)
    return success(data=svc.delete_account(request.user_obj))
