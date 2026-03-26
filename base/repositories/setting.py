import json
from typing import Optional, Any

from base.models import Setting
from base.repositories.base import BaseRepository


class SettingRepository(BaseRepository[Setting]):
    model = Setting

    def get_by_key(self, key: str) -> Optional[Setting]:
        return self.get_queryset().filter(pk=key).first()

    def get_value(self, key: str, default: Any = None) -> Any:
        setting = self.get_by_key(key)
        if setting is None:
            return default
        return self._cast_value(setting)

    def set_value(
        self,
        key: str,
        value: Any,
        value_type: str = Setting.ValueType.STRING,
        description: str = "",
    ) -> Setting:
        setting, _ = self.update_or_create(
            defaults={
                "value": self._serialize_value(value, value_type),
                "type": value_type,
                "description": description,
            },
            pk=key,
        )
        return setting

    def get_all_as_dict(self) -> dict[str, Any]:
        return {
            setting.key: self._cast_value(setting)
            for setting in self.get_all()
        }

    def delete_by_key(self, key: str) -> int:
        count, _ = self.model.objects.filter(pk=key).delete()
        return count

    @staticmethod
    def _cast_value(setting: Setting) -> Any:
        if setting.type == Setting.ValueType.INT:
            return int(setting.value)
        if setting.type == Setting.ValueType.BOOL:
            return setting.value.lower() in ("true", "1", "yes")
        if setting.type == Setting.ValueType.JSON:
            return json.loads(setting.value)
        return setting.value

    @staticmethod
    def _serialize_value(value: Any, value_type: str) -> str:
        if value_type == Setting.ValueType.JSON:
            return json.dumps(value)
        if value_type == Setting.ValueType.BOOL:
            return "true" if value else "false"
        return str(value)
