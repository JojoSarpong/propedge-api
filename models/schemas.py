from pydantic import BaseModel
from typing import List, Literal, Optional


class PickResponse(BaseModel):
    player: str
    prop: str
    line: float
    side: str
    hit_probability: float
    edge_pct: float
    tier: str
    reasoning: Optional[str] = None


class PropListResponse(BaseModel):
    date: str
    sport: str
    generated_at: str
    picks: List[PickResponse]


class SlateStatusResponse(BaseModel):
    sport: str
    date: str
    status: str
    pick_count: int = 0
    generated_at: Optional[str] = None


class V2PickResult(BaseModel):
    player: str
    prop: str
    line: float
    side: str
    hit_probability: float
    edge_pct: float
    confidence_tier: Literal['STRONG', 'SOLID', 'LEAN', 'SKIP']
    reasoning: str


class KeyProvisionRequest(BaseModel):
    owner_email: str
    tier: Literal["free", "pro"] = "free"


class KeyProvisionResponse(BaseModel):
    key: str
    owner_email: str
    tier: str
    created_at: str
    note: str = "Store this key securely — it will not be shown again."
