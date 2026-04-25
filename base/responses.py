from django.http import JsonResponse


def success(data=None, message="", status=200):
    body = {"success": True}
    if message:
        body["message"] = message
    if data is not None:
        body["data"] = data
    return JsonResponse(body, status=status)


def created(data=None, message="Created"):
    return success(data=data, message=message, status=201)


def error(message="Error", errors=None, status=400):
    body = {"success": False, "message": message}
    if errors is not None:
        body["errors"] = errors
    return JsonResponse(body, status=status)


def not_found(message="Not found"):
    return error(message=message, status=404)


def unauthorized(message="Authentication required"):
    return error(message=message, status=401)


def forbidden(message="Access denied"):
    return error(message=message, status=403)


def validation_error(errors, message="Validation failed"):
    return error(message=message, errors=errors, status=422)


def server_error(message="Internal server error"):
    return error(message=message, status=500)


def parse_page(request):
    """Safely parse page and per_page from GET params. Returns (page, per_page) or a JsonResponse error."""
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return None
    return page, per_page
