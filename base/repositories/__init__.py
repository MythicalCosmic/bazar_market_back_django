from base.repositories.base import BaseRepository, SoftDeleteRepository
from base.repositories.user import UserRepository
from base.repositories.address import AddressRepository
from base.repositories.category import CategoryRepository
from base.repositories.product import ProductRepository
from base.repositories.product_image import ProductImageRepository
from base.repositories.banner import BannerRepository
from base.repositories.cart import CartItemRepository
from base.repositories.order import (
    OrderRepository,
    OrderItemRepository,
    OrderStatusLogRepository,
)
from base.repositories.payment import PaymentRepository
from base.repositories.coupon import CouponRepository, CouponUsageRepository
from base.repositories.discount import DiscountRepository
from base.repositories.delivery import DeliveryZoneRepository
from base.repositories.notification import NotificationRepository
from base.repositories.favorite import FavoriteRepository
from base.repositories.review import ReviewRepository
from base.repositories.referral import ReferralRepository
from base.repositories.analytics import DailyStatRepository, SearchLogRepository
from base.repositories.setting import SettingRepository

__all__ = [
    "BaseRepository",
    "SoftDeleteRepository",
    "UserRepository",
    "AddressRepository",
    "CategoryRepository",
    "ProductRepository",
    "ProductImageRepository",
    "BannerRepository",
    "CartItemRepository",
    "OrderRepository",
    "OrderItemRepository",
    "OrderStatusLogRepository",
    "PaymentRepository",
    "CouponRepository",
    "CouponUsageRepository",
    "DiscountRepository",
    "DeliveryZoneRepository",
    "NotificationRepository",
    "FavoriteRepository",
    "ReviewRepository",
    "ReferralRepository",
    "DailyStatRepository",
    "SearchLogRepository",
    "SettingRepository",
]
