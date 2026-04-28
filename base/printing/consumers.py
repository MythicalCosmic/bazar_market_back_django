import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

# Group name for all connected print agents
PRINTER_GROUP = "printers"


class PrinterConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for shop print agents.

    Flow:
    1. Agent connects to ws://.../ws/printer/?token=PRINTER_SECRET
    2. Server validates token, adds agent to "printers" group
    3. When a print job is enqueued, server sends receipt data to the group
    4. Agent receives data, renders ESC/POS, prints locally
    """

    async def connect(self):
        from django.conf import settings

        # Authenticate via query param token
        query = self.scope.get("query_string", b"").decode()
        params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
        token = params.get("token", "")

        printer_secret = getattr(settings, "PRINTER_SECRET", "")
        if not printer_secret or token != printer_secret:
            logger.warning("Printer WS rejected: invalid token")
            await self.close()
            return

        # Optional: agent sends its printer_id for targeted printing
        self.printer_id = params.get("printer_id", "default")

        await self.channel_layer.group_add(PRINTER_GROUP, self.channel_name)
        await self.accept()
        logger.info(f"Printer agent connected: {self.printer_id} ({self.channel_name})")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(PRINTER_GROUP, self.channel_name)
        logger.info(f"Printer agent disconnected: {getattr(self, 'printer_id', '?')}")

    async def receive(self, text_data=None, bytes_data=None):
        # Agent can send ack/status back — log it
        if text_data:
            try:
                data = json.loads(text_data)
                logger.info(f"Printer agent message: {data}")
            except json.JSONDecodeError:
                pass

    # ── Handler for print jobs sent via channel layer ──────────

    async def print_job(self, event):
        """Receives a print job from the channel layer and forwards to the agent."""
        await self.send(text_data=json.dumps(event["data"]))
