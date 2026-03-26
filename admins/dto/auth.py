from dataclasses import dataclass


@dataclass(frozen=True)
class LoginDTO:
    username: str
    password: str

@dataclass(frozen=True)
class SessionDTO:
    ip_address: str
    user_agent: str
    device: int