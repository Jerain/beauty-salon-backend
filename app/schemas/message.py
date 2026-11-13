"""Message schemas."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class MessageResponse(BaseModel):
    id: UUID
    shop_id: UUID
    staff_id: UUID | None = None
    title: str
    content: str | None = None
    message_type: str
    is_read: bool
    related_id: UUID | None = None
    related_type: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    title: str
    content: str | None = None
    message_type: str
    staff_id: UUID | None = None
    related_id: UUID | None = None
    related_type: str | None = None


class MessageOverviewResponse(BaseModel):
    total: int = 0
    unread: int = 0
    card_expire: int = 0
    recharge: int = 0
    birthday: int = 0
    no_visit: int = 0
    appointment: int = 0
    system: int = 0


class MessageCountResponse(BaseModel):
    unread_count: int = 0


class MessageSettingResponse(BaseModel):
    id: UUID
    shop_id: UUID
    card_expire_enabled: bool
    card_expire_days: int
    recharge_enabled: bool
    birthday_enabled: bool
    birthday_days: int
    no_visit_enabled: bool
    no_visit_days: int
    appointment_enabled: bool
    appointment_hours: int
    wechat_notify_enabled: bool
    wechat_app_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageSettingUpdate(BaseModel):
    card_expire_enabled: bool | None = None
    card_expire_days: int | None = None
    recharge_enabled: bool | None = None
    birthday_enabled: bool | None = None
    birthday_days: int | None = None
    no_visit_enabled: bool | None = None
    no_visit_days: int | None = None
    appointment_enabled: bool | None = None
    appointment_hours: int | None = None
    wechat_notify_enabled: bool | None = None
    wechat_app_id: str | None = None
