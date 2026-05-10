from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UploadRead(BaseModel):
    id: int
    project_id: str
    filename: str
    size: int
    filetype: str
    uploaded_at: datetime
    parsed_text_path: str | None = None
    model_config = ConfigDict(from_attributes=True)
