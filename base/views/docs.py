import json
from pathlib import Path

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

SPEC_PATH = Path(__file__).resolve().parent.parent / "openapi.json"


@csrf_exempt
def openapi_spec_view(request):
    if SPEC_PATH.exists():
        return JsonResponse(json.loads(SPEC_PATH.read_text()), safe=False)
    return JsonResponse({"error": "Run: python manage.py export_openapi"}, status=404)


@csrf_exempt
def swagger_ui_view(request):
    html = """<!DOCTYPE html>
<html><head>
<title>Bazar Market API</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head><body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({url: '/docs/openapi.json', dom_id: '#swagger-ui'})</script>
</body></html>"""
    return HttpResponse(html, content_type="text/html")
