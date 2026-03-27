from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class Prop(BaseModel):
    id: int
    player_name: str
    team: str
    opponent: str
    stat_type: str
    line: float
    game_date: date
    source: Optional[str] = None


class PropList(BaseModel):
    props: List[Prop]


class KeyProvisionRequest(BaseModel):
    label: str


class KeyProvisionResponse(BaseModel):
    key: str
    label: str
    created_at: str
