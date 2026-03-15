"""Settings and filter rules routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.filter_rule import FilterRule
from app.models.setting import Setting
from app.models.user import User
from app.schemas.common import FilterRuleCreate, FilterRuleResponse, SettingResponse, SettingUpdate

router = APIRouter()


# ── Settings ──────────────────────────────────────────────────────────

@router.get("/", response_model=list[SettingResponse])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    """List all settings."""
    result = await db.execute(select(Setting).order_by(Setting.key))
    return result.scalars().all()


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    payload: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    """Update or create a setting by key."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = payload.value
    else:
        setting = Setting(key=key, value=payload.value)
        db.add(setting)
    await db.flush()
    await db.refresh(setting)
    return setting


# ── Filter Rules ──────────────────────────────────────────────────────

@router.get("/filter-rules", response_model=list[FilterRuleResponse])
async def list_filter_rules(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    """List all filter rules."""
    result = await db.execute(select(FilterRule).order_by(FilterRule.id))
    return result.scalars().all()


@router.post("/filter-rules", response_model=FilterRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_filter_rule(
    payload: FilterRuleCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    """Create a new filter rule."""
    rule = FilterRule(**payload.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


@router.delete("/filter-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_filter_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    """Delete a filter rule."""
    result = await db.execute(select(FilterRule).where(FilterRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    await db.delete(rule)
