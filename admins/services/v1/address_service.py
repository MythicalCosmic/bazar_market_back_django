from base.interfaces.address import IAddressRepository
from base.models import Address


class AddressService:
    def __init__(self, address_repository: IAddressRepository):
        self.address_repo = address_repository

    def get_all(self, user_id=None, is_active=None, order_by="-created_at", page=1, per_page=20):
        qs = self.address_repo.get_all().select_related("user")
        filters = {"is_active": is_active}
        if user_id is not None:
            filters["user_id"] = user_id
        qs = self.address_repo.apply_filters(qs, filters)
        qs = self.address_repo.apply_ordering(qs, order_by, {"created_at", "user_id"})
        return self.address_repo.paginate(qs, page, per_page)

    def get_by_user(self, user_id: int):
        return list(
            self.address_repo.get_by_user(user_id)
            .select_related("user")
            .order_by("-is_default", "-created_at")
        )

    def get_by_id(self, address_id: int):
        return (
            self.address_repo.get_all()
            .select_related("user")
            .filter(pk=address_id)
            .first()
        )
