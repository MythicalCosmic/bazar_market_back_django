from dataclasses import dataclass, fields


UNSET = object()


@dataclass(frozen=True)
class UpdateReviewDTO:
    admin_reply: object = UNSET

    def to_dict(self) -> dict:
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) is not UNSET
        }
