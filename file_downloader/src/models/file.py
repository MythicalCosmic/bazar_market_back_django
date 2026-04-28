from pydantic import BaseModel


class UploadResponse(BaseModel):
    id: str
    url: str
    filename: str
    content_type: str
    size: int
    duplicate: bool
