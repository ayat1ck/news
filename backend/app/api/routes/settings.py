"""Settings and filter rules routes."""

from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4

import asyncio
import qrcode
from qrcode.image.svg import SvgPathImage
from telethon import TelegramClient
from telethon.errors import (
    ApiIdInvalidError,
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.filter_rule import FilterRule
from app.models.setting import Setting
from app.models.user import User
from app.schemas.common import (
    FilterRuleCreate,
    FilterRuleResponse,
    SettingResponse,
    SettingUpdate,
    TelegramAuthCompleteRequest,
    TelegramAuthResponse,
    TelegramAuthStartRequest,
    TelegramQrStartRequest,
    TelegramQrStartResponse,
    TelegramQrStatusResponse,
)

router = APIRouter()
_telegram_qr_sessions: dict[str, dict[str, object]] = {}


async def _get_setting(db: AsyncSession, key: str) -> Setting | None:
    result = await db.execute(select(Setting).where(Setting.key == key))
    return result.scalar_one_or_none()


async def _set_setting(db: AsyncSession, key: str, value: str, description: str | None = None) -> Setting:
    setting = await _get_setting(db, key)
    if setting is None:
        setting = Setting(key=key, value=value, description=description)
        db.add(setting)
    else:
        setting.value = value
        if description and not setting.description:
            setting.description = description
    await db.flush()
    return setting


def _cleanup_qr_sessions() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    expired_ids = [
        auth_id
        for auth_id, session in _telegram_qr_sessions.items()
        if session["created_at"] < cutoff
    ]
    for auth_id in expired_ids:
        session = _telegram_qr_sessions.pop(auth_id, None)
        client = session.get("client") if session else None
        if client is not None:
            asyncio.create_task(client.disconnect())


def _build_qr_svg(data: str) -> str:
    image = qrcode.make(data, image_factory=SvgPathImage)
    buffer = BytesIO()
    image.save(buffer)
    return buffer.getvalue().decode("utf-8")


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
    if key == "collection_interval_minutes":
        try:
            minutes = int(payload.value)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interval must be an integer") from exc
        if minutes < 5 or minutes > 1440:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interval must be between 5 and 1440 minutes",
            )

    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = payload.value
    else:
        setting = Setting(key=key, value=payload.value)
        db.add(setting)
    await db.flush()
    await db.commit()
    await db.refresh(setting)
    return setting


@router.post("/telegram-auth/start", response_model=TelegramAuthResponse)
async def start_telegram_auth(
    payload: TelegramAuthStartRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    """Send Telegram login code and persist temporary auth state."""
    try:
        api_id = int(payload.api_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API ID must be an integer") from exc

    client = TelegramClient(StringSession(), api_id, payload.api_hash)
    await client.connect()
    try:
        sent = await client.send_code_request(payload.phone.strip())
    except ApiIdInvalidError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid API ID or API HASH") from exc
    except PhoneNumberInvalidError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number") from exc
    finally:
        await client.disconnect()

    await _set_setting(db, "telegram_api_id", str(api_id), "Telegram API ID for source collection")
    await _set_setting(db, "telegram_api_hash", payload.api_hash.strip(), "Telegram API HASH for source collection")
    await _set_setting(db, "telegram_login_phone", payload.phone.strip(), "Temporary Telegram auth phone")
    await _set_setting(
        db,
        "telegram_login_phone_code_hash",
        sent.phone_code_hash,
        "Temporary Telegram auth phone code hash",
    )
    await db.commit()

    return TelegramAuthResponse(
        success=True,
        message="Код отправлен в Telegram. Введите его в следующем шаге.",
    )


@router.post("/telegram-auth/qr/start", response_model=TelegramQrStartResponse)
async def start_telegram_qr_auth(
    payload: TelegramQrStartRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    """Start Telegram QR login flow and return SVG QR image."""
    _cleanup_qr_sessions()
    try:
        api_id = int(payload.api_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API ID must be an integer") from exc

    client = TelegramClient(StringSession(), api_id, payload.api_hash.strip())
    await client.connect()
    try:
        qr_login = await client.qr_login()
    except ApiIdInvalidError as exc:
        await client.disconnect()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid API ID or API HASH") from exc

    auth_id = uuid4().hex
    _telegram_qr_sessions[auth_id] = {
        "client": client,
        "qr_login": qr_login,
        "api_id": str(api_id),
        "api_hash": payload.api_hash.strip(),
        "created_at": datetime.now(timezone.utc),
    }

    await _set_setting(db, "telegram_api_id", str(api_id), "Telegram API ID for source collection")
    await _set_setting(db, "telegram_api_hash", payload.api_hash.strip(), "Telegram API HASH for source collection")
    await db.commit()

    return TelegramQrStartResponse(
        success=True,
        message="QR-код готов. Откройте Telegram -> Настройки -> Устройства -> Подключить устройство.",
        auth_id=auth_id,
        qr_svg=_build_qr_svg(qr_login.url),
    )


@router.get("/telegram-auth/qr/status/{auth_id}", response_model=TelegramQrStatusResponse)
async def telegram_qr_auth_status(
    auth_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    """Poll Telegram QR login status."""
    _cleanup_qr_sessions()
    session = _telegram_qr_sessions.get(auth_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR-сессия не найдена или истекла")

    client: TelegramClient = session["client"]  # type: ignore[assignment]
    qr_login = session["qr_login"]
    try:
        await asyncio.wait_for(qr_login.wait(), timeout=0.2)
    except TimeoutError:
        return TelegramQrStatusResponse(
            success=True,
            status="pending",
            message="Ожидается подтверждение входа в Telegram.",
        )
    except SessionPasswordNeededError:
        return TelegramQrStatusResponse(
            success=False,
            status="password_required",
            message="Для этого аккаунта включен пароль 2FA. Используйте вход по коду.",
        )

    if not await client.is_user_authorized():
        return TelegramQrStatusResponse(
            success=True,
            status="pending",
            message="Подтверждение еще не завершено.",
        )

    session_string = client.session.save()
    await _set_setting(
        db,
        "telegram_session_string",
        session_string,
        "Telegram session string for source collection",
    )
    await db.commit()

    await client.disconnect()
    _telegram_qr_sessions.pop(auth_id, None)

    return TelegramQrStatusResponse(
        success=True,
        status="authorized",
        message="Telegram-сессия сохранена. Сбор Telegram-источников готов к работе.",
        session_string=session_string,
    )


@router.post("/telegram-auth/complete", response_model=TelegramAuthResponse)
async def complete_telegram_auth(
    payload: TelegramAuthCompleteRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    """Complete Telegram login and save session string in database settings."""
    api_id_setting = await _get_setting(db, "telegram_api_id")
    api_hash_setting = await _get_setting(db, "telegram_api_hash")
    phone_setting = await _get_setting(db, "telegram_login_phone")
    code_hash_setting = await _get_setting(db, "telegram_login_phone_code_hash")

    if not all([api_id_setting, api_hash_setting, phone_setting, code_hash_setting]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сначала отправьте код авторизации.",
        )

    client = TelegramClient(StringSession(), int(api_id_setting.value), api_hash_setting.value or "")
    await client.connect()
    try:
        try:
            await client.sign_in(
                phone=phone_setting.value or "",
                code=payload.code.strip(),
                phone_code_hash=code_hash_setting.value or "",
            )
        except SessionPasswordNeededError:
            if not payload.password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Для этого аккаунта требуется пароль двухфакторной защиты.",
                )
            try:
                await client.sign_in(password=payload.password)
            except PasswordHashInvalidError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный пароль 2FA") from exc
        except PhoneCodeInvalidError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный код") from exc
        except PhoneCodeExpiredError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Код истек") from exc

        if not await client.is_user_authorized():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Авторизация не завершена")

        session_string = client.session.save()
    finally:
        await client.disconnect()

    await _set_setting(
        db,
        "telegram_session_string",
        session_string,
        "Telegram session string for source collection",
    )
    await db.commit()

    return TelegramAuthResponse(
        success=True,
        message="Telegram-сессия сохранена. Сбор Telegram-источников готов к работе.",
        session_string=session_string,
    )


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
    await db.commit()
