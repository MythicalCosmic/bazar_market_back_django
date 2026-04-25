import logging
import threading
from queue import Queue

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_print_queue = Queue()


def enqueue_print(order_id: int):
    """Add an order to the print queue and process."""
    _print_queue.put(order_id)
    # Process in a separate thread so the API call returns immediately
    threading.Thread(target=_process_queue, daemon=True).start()


def _process_queue():
    """Process queued prints with a lock — one at a time."""
    with _lock:
        while not _print_queue.empty():
            order_id = _print_queue.get()
            try:
                _print_order(order_id)
                logger.info(f"Printed order {order_id}")
            except Exception as e:
                logger.error(f"Failed to print order {order_id}: {e}")
            finally:
                _print_queue.task_done()


def _print_order(order_id: int):
    from base.models import Order
    order = (
        Order.objects
        .select_related("user")
        .prefetch_related("items")
        .get(pk=order_id)
    )
    from base.printing.printing_service import print_order_receipt
    print_order_receipt(order)
