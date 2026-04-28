import logging

logger = logging.getLogger(__name__)


def notify_admins_new_order(order):
    """Send Telegram notification to all admin users about a new order."""
    try:
        from bot.tasks import task_notify_admins_new_order
        task_notify_admins_new_order.delay(order.id)
    except Exception as e:
        logger.warning(f"Failed to enqueue admin notification: {e}")


def notify_customer_status_change(order):
    """Notify customer via Telegram when order status changes."""
    try:
        from bot.tasks import task_notify_customer_status
        task_notify_customer_status.delay(order.id)
    except Exception as e:
        logger.warning(f"Failed to enqueue status notification: {e}")


def notify_customers_new_banner(banner):
    """Broadcast a new banner to all customers with telegram_id."""
    try:
        from bot.tasks import task_broadcast_banner
        task_broadcast_banner.delay(banner.id)
    except Exception as e:
        logger.warning(f"Failed to enqueue banner broadcast: {e}")


def notify_cart_price_change(product, old_price, new_price):
    """Notify customers who have this product in their cart about a price change."""
    try:
        from bot.tasks import task_notify_cart_price_change
        task_notify_cart_price_change.delay(product.id, str(old_price), str(new_price))
    except Exception as e:
        logger.warning(f"Failed to enqueue price change notification: {e}")


def notify_referral_reward(referrer, coupon_code):
    """Notify referrer via Telegram about their reward coupon."""
    try:
        from bot.tasks import task_notify_referral_reward
        task_notify_referral_reward.delay(referrer.id, coupon_code)
    except Exception as e:
        logger.warning(f"Failed to enqueue referral reward notification: {e}")
