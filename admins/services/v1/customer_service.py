from base.interfaces.user import IUserRepository
from base.exceptions import NotFoundError, ValidationError
from admins.dto.customer import UpdateCustomerDTO
from base.models import User


class CustomerService:
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    def _customers_qs(self):
        return self.user_repository.get_all().filter(role=User.Role.CLIENT)

    def get_all(self, query=None, is_active=None, order_by="-created_at", page=1, per_page=20):
        qs = self._customers_qs()
        qs = self.user_repository.search(qs, query, ["first_name", "last_name", "phone", "telegram_id"])
        qs = self.user_repository.apply_filters(qs, {"is_active": is_active})
        qs = self.user_repository.apply_ordering(qs, order_by, {"created_at", "first_name", "last_name"})
        return self.user_repository.paginate(qs, page, per_page)

    def get_by_id(self, customer_id: int) -> User | None:
        return (
            self._customers_qs()
            .prefetch_related("addresses", "orders", "favorites__product", "reviews__order")
            .filter(pk=customer_id)
            .first()
        )

    def update_customer(self, customer_id: int, dto: UpdateCustomerDTO) -> dict:
        customer = self._customers_qs().filter(pk=customer_id).first()
        if not customer:
            raise NotFoundError("Customer not found")

        data = dto.to_dict()
        if "phone" in data and data["phone"] != customer.phone:
            if self.user_repository.exists(phone=data["phone"]):
                raise ValidationError("Phone already exists")

        if data:
            self.user_repository.update(customer, **data)

        return {
            "id": customer.id,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "phone": customer.phone,
        }

    def deactivate(self, customer_id: int) -> dict:
        customer = self._customers_qs().filter(pk=customer_id).first()
        customer_deactivate = self._customers_qs().filter(pk=customer_id, is_active=False)
        if customer_deactivate:
            raise NotFoundError("This customer is already deactive")
        if not customer:
            raise NotFoundError("Customer not found")

        self.user_repository.deactivate(customer)
        return {"message": "Customer deactivated"}

    def activate(self, customer_id: int) -> dict:
        customer = self.user_repository.get_all().filter(
            pk=customer_id, role=User.Role.CLIENT, is_active=False
        ).first()
        if not customer:
            raise NotFoundError("Customer not found or already active")

        self.user_repository.activate(customer)
        return {"message": "Customer activated"}
