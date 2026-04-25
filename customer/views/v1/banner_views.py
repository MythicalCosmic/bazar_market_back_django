from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from base.container import container
from base.responses import success
from customer.services.v1.banner_service import CustomerBannerService


def _serialize_banner(b) -> dict:
    return {
        "id": b.id,
        "title": b.title,
        "image": b.image,
        "link_type": b.link_type,
        "link_value": b.link_value,
    }


@csrf_exempt
@require_GET
def list_banners_view(request):
    svc = container.resolve(CustomerBannerService)
    banners = svc.get_active_banners()
    return success(data=[_serialize_banner(b) for b in banners])
