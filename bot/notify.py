import logging

logger = logging.getLogger(__name__)


def _via_celery(task, *args):
    """Enqueue via Celery .delay(). On failure (broker down), log and drop —
    the synchronous fallback used to crash because bind=True tasks expect a
    self argument that direct calls don't supply."""
    try:
        task.delay(*args)
    except Exception:
        logger.exception("Failed to enqueue Celery task %s; notification dropped", task.name)


def notify_admins_new_order(order):
    from bot.tasks import task_notify_admins_new_order
    _via_celery(task_notify_admins_new_order, order.id)


def notify_customer_status_change(order):
    from bot.tasks import task_notify_customer_status
    _via_celery(task_notify_customer_status, order.id)


def notify_customers_new_banner(banner):
    from bot.tasks import task_broadcast_banner
    _via_celery(task_broadcast_banner, banner.id)


def notify_cart_price_change(product, old_price, new_price):
    from bot.tasks import task_notify_cart_price_change
    _via_celery(task_notify_cart_price_change, product.id, str(old_price), str(new_price))


def notify_referral_reward(referrer, coupon_code):
    from bot.tasks import task_notify_referral_reward
    _via_celery(task_notify_referral_reward, referrer.id, coupon_code)
