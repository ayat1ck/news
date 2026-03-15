"""Dashboard and settings schemas."""

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_sources: int
    active_sources: int
    total_raw_items: int
    new_raw_items: int
    total_canonical_items: int
    pending_moderation: int
    published_items: int
    duplicates_detected: int


class SettingUpdate(BaseModel):
    value: str


class SettingResponse(BaseModel):
    id: int
    key: str
    value: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class FilterRuleCreate(BaseModel):
    rule_type: str
    pattern: str
    description: str | None = None
    is_active: bool = True


class FilterRuleResponse(BaseModel):
    id: int
    rule_type: str
    pattern: str
    description: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}
