from typing import TypeVar, Any, get_type_hints

T = TypeVar("T")


class Container:

    def __init__(self) -> None:
        self._bindings: dict[type, tuple[type, bool]] = {}
        self._singletons: dict[type, Any] = {}

    def register(
        self, interface: type, implementation: type, *, singleton: bool = True
    ) -> "Container":
        self._bindings[interface] = (implementation, singleton)
        return self

    def register_instance(self, interface: type, instance: Any) -> "Container":
        self._singletons[interface] = instance
        self._bindings[interface] = (type(instance), True)
        return self

    def resolve(self, abstract: type[T]) -> T:
        if abstract in self._bindings:
            impl_class, is_singleton = self._bindings[abstract]
            if is_singleton and abstract in self._singletons:
                return self._singletons[abstract]
            instance = self._build(impl_class)
            if is_singleton:
                self._singletons[abstract] = instance
            return instance
        if not getattr(abstract, "__abstractmethods__", None):
            return self._build(abstract)
        raise LookupError(f"No binding registered for {abstract.__name__}")

    def _build(self, cls: type) -> Any:
        init = cls.__init__
        if init is object.__init__:
            return cls()
        try:
            hints = get_type_hints(init)
        except Exception:
            return cls()
        hints.pop("return", None)
        kwargs = {}
        for name, hint in hints.items():
            kwargs[name] = self.resolve(hint)
        return cls(**kwargs)

    def is_registered(self, interface: type) -> bool:
        return interface in self._bindings

    def reset(self) -> None:
        self._singletons.clear()


container = Container()


def configure(c: Container | None = None) -> Container:
    if c is None:
        c = container

    from base.interfaces import (
        IUserRepository,
        IAddressRepository,
        ICategoryRepository,
        IProductRepository,
        IProductImageRepository,
        IBannerRepository,
        ICartItemRepository,
        IOrderRepository,
        IOrderItemRepository,
        IOrderStatusLogRepository,
        IPaymentRepository,
        ICouponRepository,
        ICouponUsageRepository,
        IDiscountRepository,
        IDeliveryZoneRepository,
        INotificationRepository,
        IFavoriteRepository,
        IReviewRepository,
        IReferralRepository,
        IDailyStatRepository,
        ISearchLogRepository,
        ISettingRepository,
        ISessionRepository
    )
    from base.repositories import (
        UserRepository,
        AddressRepository,
        CategoryRepository,
        ProductRepository,
        ProductImageRepository,
        BannerRepository,
        CartItemRepository,
        OrderRepository,
        OrderItemRepository,
        OrderStatusLogRepository,
        PaymentRepository,
        CouponRepository,
        CouponUsageRepository,
        DiscountRepository,
        DeliveryZoneRepository,
        NotificationRepository,
        FavoriteRepository,
        ReviewRepository,
        ReferralRepository,
        DailyStatRepository,
        SearchLogRepository,
        SettingRepository,
        SessionRepository
    )

    c.register(IUserRepository, UserRepository)
    c.register(IAddressRepository, AddressRepository)
    c.register(ICategoryRepository, CategoryRepository)
    c.register(IProductRepository, ProductRepository)
    c.register(IProductImageRepository, ProductImageRepository)
    c.register(ISessionRepository, SessionRepository)
    c.register(IBannerRepository, BannerRepository)
    c.register(ICartItemRepository, CartItemRepository)
    c.register(IOrderRepository, OrderRepository)
    c.register(IOrderItemRepository, OrderItemRepository)
    c.register(IOrderStatusLogRepository, OrderStatusLogRepository)
    c.register(IPaymentRepository, PaymentRepository)
    c.register(ICouponRepository, CouponRepository)
    c.register(ICouponUsageRepository, CouponUsageRepository)
    c.register(IDiscountRepository, DiscountRepository)
    c.register(IDeliveryZoneRepository, DeliveryZoneRepository)
    c.register(INotificationRepository, NotificationRepository)
    c.register(IFavoriteRepository, FavoriteRepository)
    c.register(IReviewRepository, ReviewRepository)
    c.register(IReferralRepository, ReferralRepository)
    c.register(IDailyStatRepository, DailyStatRepository)
    c.register(ISearchLogRepository, SearchLogRepository)
    c.register(ISettingRepository, SettingRepository)

    return c
