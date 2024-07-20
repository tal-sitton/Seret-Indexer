from pydantic import BaseModel


class SiteInfoModel(BaseModel):
    mid: str
    url: str
    priority: float
