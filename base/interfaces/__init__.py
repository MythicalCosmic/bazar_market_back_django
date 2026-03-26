from base.interfaces.base import IBaseRepository, ISoftDeleteRepository
from base.interfaces.user import IUserRepository
from base.interfaces.address import IAddressRepository
from base.interfaces.category import ICategoryRepository
from base.interfaces.product import IProductRepository
from base.interfaces.product_image import IProductImageRepository
from base.interfaces.banner import IBannerRepository
from base.interfaces.cart import ICartItemRepository
from base.interfaces.order import (
    IOrderRepository,
    IOrderItemRepository,
    IOrderStatusLogRepository,
)
from base.interfaces.payment import IPaymentRepository
from base.interfaces.coupon import ICouponRepository, ICouponUsageRepository
from base.interfaces.discount import IDiscountRepository
from base.interfaces.delivery import IDeliveryZoneRepository
from base.interfaces.notification import INotificationRepository
from base.interfaces.favorite import IFavoriteRepository
from base.interfaces.review import IReviewRepository
from base.interfaces.referral import IReferralRepository
from base.interfaces.analytics import IDailyStatRepository, ISearchLogRepository
from base.interfaces.setting import ISettingRepository
from base.interfaces.session import ISessionRepository
__all__ = [
    "IBaseRepository",
    "ISoftDeleteRepository",
    "IUserRepository",
    "IAddressRepository",
    "ICategoryRepository",
    "IProductRepository",
    "IProductImageRepository",
    "IBannerRepository",
    "ICartItemRepository",
    "IOrderRepository",
    "IOrderItemRepository",
    "IOrderStatusLogRepository",
    "IPaymentRepository",
    "ICouponRepository",
    "ICouponUsageRepository",
    "IDiscountRepository",
    "IDeliveryZoneRepository",
    "INotificationRepository",
    "IFavoriteRepository",
    "IReviewRepository",
    "IReferralRepository",
    "IDailyStatRepository",
    "ISearchLogRepository",
    "ISettingRepository",
    "ISessionRepository"
]
