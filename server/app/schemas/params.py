from typing import Any
from pydantic import BaseModel


class ParamPatch(BaseModel):
    key: str
    value: Any
