from dataclasses import dataclass


@dataclass(frozen=True)
class RegisterDTO:
    phone: str
    first_name: str
    last_name: str = ""
    language: str = "uz"
    telegram_id: int | None = None


@dataclass(frozen=True)
class SessionDTO:
    ip_address: str
    user_agent: str
    device: str = ""
