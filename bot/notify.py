import asyncio
import logging

logger = logging.getLogger(__name__)


def _send_async(coro):
    """Bridge sync Django context to async bot sending."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        asyncio.run(coro)


def _via_celery(task, *args):
    """Try Celery .delay(), fall back to direct execution."""
    try:
        task.delay(*args)
    except Exception:
        # Celery not available — run the task function directly (sync)
        try:
            task(*args)
        except Exception as e:
            logger.warning(f"Direct task execution failed: {e}")


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
