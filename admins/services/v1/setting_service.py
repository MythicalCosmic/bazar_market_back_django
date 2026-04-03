from base.interfaces.setting import ISettingRepository
from base.exceptions import NotFoundError, ValidationError
from base.models import Setting
from admins.dto.setting import SetSettingDTO


class SettingService:
    def __init__(self, setting_repository: ISettingRepository):
        self.setting_repo = setting_repository

    def get_all(self) -> list[dict]:
        settings = list(self.setting_repo.get_all().order_by("key"))
        return [
            {
                "key": s.key,
                "value": self.setting_repo._cast_value(s),
                "type": s.type,
                "description": s.description,
                "updated_at": s.updated_at.isoformat(),
            }
            for s in settings
        ]

    def get_by_key(self, key: str) -> dict:
        setting = self.setting_repo.get_by_key(key)
        if not setting:
            raise NotFoundError(f"Setting '{key}' not found")
        return {
            "key": setting.key,
            "value": self.setting_repo._cast_value(setting),
            "type": setting.type,
            "description": setting.description,
            "updated_at": setting.updated_at.isoformat(),
        }

    def set_value(self, dto: SetSettingDTO) -> dict:
        if dto.type not in dict(Setting.ValueType.choices):
            raise ValidationError(f"Invalid type: {dto.type}")

        self.setting_repo.set_value(
            key=dto.key,
            value=dto.value,
            value_type=dto.type,
            description=dto.description,
        )
        return {"key": dto.key, "message": "Setting saved"}

    def delete(self, key: str) -> dict:
        count = self.setting_repo.delete_by_key(key)
        if not count:
            raise NotFoundError(f"Setting '{key}' not found")
        return {"message": f"Setting '{key}' deleted"}

    def get_as_dict(self) -> dict:
        return self.setting_repo.get_all_as_dict()
