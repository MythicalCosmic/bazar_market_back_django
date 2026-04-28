"""
ASGI config for bazar_market_django project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bazar_market_django.settings')

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

from telescope.routing import websocket_urlpatterns as telescope_ws
from base.printing.routing import websocket_urlpatterns as printer_ws

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(
        # Printer WS: token-authenticated, no origin check needed
        printer_ws
        # Telescope WS: browser-based, origin validated
        + telescope_ws
    ),
})
