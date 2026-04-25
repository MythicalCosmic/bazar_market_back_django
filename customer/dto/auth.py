from dataclasses import dataclass


@dataclass(frozen=True)
class RegisterDTO:
    phone: str
    first_name: str
    password: str
    last_name: str = ""
    language: str = "uz"
    telegram_id: int | None = None


@dataclass(frozen=True)
class LoginDTO:
    phone: str
    password: str


@dataclass(frozen=True)
class SessionDTO:
    ip_address: str
    user_agent: str
    device: str = ""
