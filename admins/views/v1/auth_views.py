from base.container import container
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from admins.services.v1.auth_service import AuthService
from admins.dto.auth import LoginDTO, SessionDTO

@csrf_exempt
@require_POST
def login_view(request):
    try:
        #retrive the data from the request
        data = json.loads(request.body)

        #map the data to DTOS
        login_dto = LoginDTO(username=data.get("username"), password=data.get("password"))
        session_dto = SessionDTO(ip_address=request.META.get("REMOTE_ADDR"), user_agent=request.META.get("HTTP_USER_AGENT", ""), device=request.META.get("device", "Unknown device"))

        #resolve the service from dependency injection
        auth_service = container.resolve(AuthService)

        #execute the logic
        result = auth_service.login(login_dto, session_dto)
        return result

    except Exception as e:
        print(e)