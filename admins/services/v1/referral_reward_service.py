from decimal import Decimal, InvalidOperation

from base.interfaces.reward import IReferralRewardRepository
from base.interfaces.product import IProductRepository
from base.exceptions import NotFoundError, ValidationError
from admins.dto.referral_reward import CreateReferralRewardDTO, UpdateReferralRewardDTO
from base.models import ReferralReward


VALID_TYPES = set(dict(ReferralReward.Type.choices).keys())
VALID_COUPON_TYPES = {"percent", "fixed"}


class ReferralRewardService:
    def __init__(
        self,
        referral_reward_repository: IReferralRewardRepository,
        product_repository: IProductRepository,
    ):
        self.reward_repo = referral_reward_repository
        self.product_repo = product_repository

    def get_all(self, order_by="-created_at", page=1, per_page=20):
        qs = self.reward_repo.get_all()
        qs = self.reward_repo.apply_ordering(qs, order_by, {"created_at", "name", "type"})
        return self.reward_repo.paginate(qs, page, per_page)

    def get_by_id(self, reward_id: int):
        return self.reward_repo.get_by_id(reward_id)

    def create_reward(self, dto: CreateReferralRewardDTO) -> dict:
        if dto.type not in VALID_TYPES:
            raise ValidationError(f"Invalid type. Must be one of: {', '.join(VALID_TYPES)}")

        kwargs = {
            "name": dto.name,
            "type": dto.type,
            "is_active": dto.is_active,
        }

        if dto.type == "coupon":
            self._validate_coupon_fields(dto.coupon_type, dto.coupon_value)
            kwargs.update({
                "coupon_type": dto.coupon_type,
                "coupon_value": Decimal(dto.coupon_value) if dto.coupon_value else None,
                "coupon_max_discount": Decimal(dto.coupon_max_discount) if dto.coupon_max_discount else None,
                "coupon_min_order": Decimal(dto.coupon_min_order) if dto.coupon_min_order else None,
                "coupon_expires_days": dto.coupon_expires_days,
            })
        elif dto.type == "free_delivery":
            if dto.free_delivery_count < 1:
                raise ValidationError("free_delivery_count must be at least 1")
            kwargs["free_delivery_count"] = dto.free_delivery_count
        elif dto.type == "bonus_product":
            if not dto.bonus_product_id:
                raise ValidationError("bonus_product_id is required for bonus_product type")
            product = self.product_repo.get_by_id(dto.bonus_product_id)
            if not product:
                raise ValidationError("Product not found")
            kwargs["bonus_product"] = product
            kwargs["bonus_quantity"] = Decimal(dto.bonus_quantity)

        if dto.is_active:
            self.reward_repo.deactivate_all()

        reward = self.reward_repo.create(**kwargs)
        return {"id": reward.id, "name": reward.name, "type": reward.type}

    def update_reward(self, reward_id: int, dto: UpdateReferralRewardDTO) -> dict:
        reward = self.reward_repo.get_by_id(reward_id)
        if not reward:
            raise NotFoundError("Referral reward not found")

        data = dto.to_dict()

        if "type" in data and data["type"] not in VALID_TYPES:
            raise ValidationError(f"Invalid type. Must be one of: {', '.join(VALID_TYPES)}")

        if "coupon_type" in data and data["coupon_type"] not in VALID_COUPON_TYPES:
            raise ValidationError("coupon_type must be 'percent' or 'fixed'")

        if "bonus_product_id" in data:
            pid = data.pop("bonus_product_id")
            if pid is not None:
                product = self.product_repo.get_by_id(pid)
                if not product:
                    raise ValidationError("Product not found")
                data["bonus_product"] = product
            else:
                data["bonus_product"] = None

        for decimal_field in ("coupon_value", "coupon_max_discount", "coupon_min_order", "bonus_quantity"):
            if decimal_field in data and data[decimal_field] is not None:
                try:
                    data[decimal_field] = Decimal(str(data[decimal_field]))
                except InvalidOperation:
                    raise ValidationError(f"Invalid value for {decimal_field}")

        if data:
            self.reward_repo.update(reward, **data)

        return {"id": reward.id, "name": reward.name, "type": reward.type}

    def delete_reward(self, reward_id: int) -> dict:
        reward = self.reward_repo.get_by_id(reward_id)
        if not reward:
            raise NotFoundError("Referral reward not found")
        self.reward_repo.delete(reward)
        return {"message": "Referral reward deleted"}

    def activate(self, reward_id: int) -> dict:
        reward = self.reward_repo.get_by_id(reward_id)
        if not reward:
            raise NotFoundError("Referral reward not found")
        self.reward_repo.activate(reward)
        return {"message": f"'{reward.name}' is now the active referral reward"}

    def deactivate(self, reward_id: int) -> dict:
        reward = self.reward_repo.get_by_id(reward_id)
        if not reward:
            raise NotFoundError("Referral reward not found")
        self.reward_repo.deactivate(reward)
        return {"message": "Referral reward deactivated"}

    def _validate_coupon_fields(self, coupon_type, coupon_value):
        if coupon_type not in VALID_COUPON_TYPES:
            raise ValidationError("coupon_type must be 'percent' or 'fixed'")
        if not coupon_value:
            raise ValidationError("coupon_value is required for coupon type")
        try:
            val = Decimal(coupon_value)
            if val <= 0:
                raise ValidationError("coupon_value must be positive")
        except InvalidOperation:
            raise ValidationError("Invalid coupon_value")
