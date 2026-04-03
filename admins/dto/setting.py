from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class SetSettingDTO:
    key: str
    value: Any
    type: str = "string"
    description: str = ""
