"""Appointment router - Full appointment lifecycle management."""
from typing import Optional
from uuid import UUID
from datetime import datetime, date, time, timedelta
from datetime import date as date_type  # alias to avoid shadowing by query param name
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.appointment import Appointment, AppointmentSetting, TimeSlotOccupy
from app.schemas.appointment import (
    AppointmentResponse, AppointmentCreate, AppointmentBatchCreate,
    AppointmentUpdate, AppointmentStatusUpdate,
    ConflictCheckRequest, ConflictCheckResponse,
    DayCountResponse,
    TimeSlotOccupyResponse, TimeSlotOccupyCreate, TimeSlotOccupyUpdate,
    AppointmentSettingResponse, AppointmentSettingUpdate,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.middleware.auth import get_effective_shop_ids, get_current_staff

router = APIRouter(prefix="/api", tags=["预约管理"])


# ============ Helper ============

def _build_appointment_response(a: Appointment) -> AppointmentResponse:
    """Build response without lazy loading."""
    cust = getattr(a, "customer", None)
    stf = getattr(a, "staff", None)
    rm = getattr(a, "room", None)
    proj = getattr(a, "project", None)
    return AppointmentResponse(
        id=a.id, customer_id=a.customer_id,
        customer_name=cust.name if cust else None,
        staff_id=a.staff_id, staff_name=stf.name if stf else None,
        shop_id=a.shop_id, room_id=a.room_id,
        room_name=rm.name if rm else None,
        project_id=a.project_id,
        project_name=proj.name if proj else None,
        project_ids=a.project_ids,
        appointment_date=a.appointment_date,
        start_time=str(a.start_time) if a.start_time else None,
        duration=a.duration, status=a.status,
        source=a.source, remark=a.remark,
        cancel_reason=a.cancel_reason,
        confirmed_at=a.confirmed_at, arrived_at=a.arrived_at,
        completed_at=a.completed_at, cancelled_at=a.cancelled_at,
        created_at=a.created_at,
    )


def _parse_time(t: str) -> time:
    """Parse time string to time object."""
    parts = t.split(":")
    return time(int(parts[0]), int(parts[1]))


def _time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _check_overlap(s1: time, e1: time, s2: time, e2: time) -> bool:
    """Check if two time ranges overlap."""
    m1s, m1e = _time_to_minutes(s1), _time_to_minutes(e1)
    m2s, m2e = _time_to_minutes(s2), _time_to_minutes(e2)
    return m1s < m2e and m2s < m1e


# ============ Appointments CRUD ============

@router.get("/appointments", response_model=PaginatedResponse[AppointmentResponse])
async def list_appointments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    appointment_date: Optional[date_type] = Query(None, alias="date"),
    staff_id: Optional[UUID] = None,
    customer_id: Optional[UUID] = None,
    status: Optional[str] = None,
    start_date: Optional[date_type] = None,
    end_date: Optional[date_type] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated appointment list with filters."""
    query = (
        select(Appointment)
        .where(Appointment.shop_id.in_(shop_ids))
        .options(
            selectinload(Appointment.customer),
            selectinload(Appointment.staff),
            selectinload(Appointment.room),
            selectinload(Appointment.project),
        )
    )
    if appointment_date:
        query = query.where(Appointment.appointment_date == appointment_date)
    if start_date:
        query = query.where(Appointment.appointment_date >= start_date)
    if end_date:
        query = query.where(Appointment.appointment_date <= end_date)
    if staff_id:
        query = query.where(Appointment.staff_id == staff_id)
    if customer_id:
        query = query.where(Appointment.customer_id == customer_id)
    if status:
        query = query.where(Appointment.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Appointment.appointment_date.desc(), Appointment.start_time)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    appointments = result.scalars().unique().all()
    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[_build_appointment_response(a) for a in appointments],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


# ============ Conflict Check ============

@router.post("/appointments/check-conflict", response_model=ConflictCheckResponse)
async def check_conflict(
    data: ConflictCheckRequest,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Check if a time slot has conflicts."""
    start_t = _parse_time(data.start_time)
    end_minutes = _time_to_minutes(start_t) + data.duration
    end_t = time(end_minutes // 60, end_minutes % 60)

    query = select(Appointment).where(
        Appointment.staff_id == data.staff_id,
        Appointment.appointment_date == data.appointment_date,
        Appointment.status.in_(["pending", "confirmed"]),
    )
    if data.exclude_id:
        query = query.where(Appointment.id != data.exclude_id)

    existing = (await db.execute(query)).scalars().all()
    conflicts = []
    for ex in existing:
        ex_start = _time_to_minutes(ex.start_time)
        ex_end = ex_start + ex.duration
        if _check_overlap(start_t, end_t, ex.start_time, time(ex_end // 60, ex_end % 60)):
            conflicts.append({
                "id": str(ex.id),
                "start_time": str(ex.start_time),
                "duration": ex.duration,
                "status": ex.status,
            })

    # Also check occupied slots
    occupies = (await db.execute(
        select(TimeSlotOccupy).where(
            TimeSlotOccupy.staff_id == data.staff_id,
            TimeSlotOccupy.occupy_date == data.appointment_date,
        )
    )).scalars().all()

    for occ in occupies:
        if _check_overlap(start_t, end_t, occ.start_time, occ.end_time):
            conflicts.append({
                "type": "occupy",
                "start_time": str(occ.start_time),
                "end_time": str(occ.end_time),
                "reason": occ.reason,
            })

    return ConflictCheckResponse(
        available=len(conflicts) == 0,
        conflicts=conflicts,
        suggestion="该时段有冲突，请选择其他时段" if conflicts else None,
    )


# ============ Day Count ============

@router.get("/appointments/day-count", response_model=list[DayCountResponse])
async def get_day_count(
    start_date: date = Query(...),
    end_date: date = Query(...),
    staff_id: Optional[UUID] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get appointment count by day in a date range."""
    query = (
        select(
            Appointment.appointment_date,
            func.count().label("total"),
            func.sum(case((Appointment.status == "confirmed", 1), else_=0)).label("confirmed"),
            func.sum(case((Appointment.status == "pending", 1), else_=0)).label("pending"),
        )
        .where(
            Appointment.shop_id.in_(shop_ids),
            Appointment.appointment_date >= start_date,
            Appointment.appointment_date <= end_date,
            Appointment.status.in_(["pending", "confirmed", "arrived", "completed"]),
        )
        .group_by(Appointment.appointment_date)
        .order_by(Appointment.appointment_date)
    )
    if staff_id:
        query = query.where(Appointment.staff_id == staff_id)

    result = await db.execute(query)
    rows = result.all()

    return [
        DayCountResponse(
            date=str(row[0]),
            count=row[1],
            confirmed_count=row[2] or 0,
            pending_count=row[3] or 0,
        )
        for row in rows
    ]


@router.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get appointment detail."""
    result = await db.execute(
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .options(
            selectinload(Appointment.customer),
            selectinload(Appointment.staff),
            selectinload(Appointment.room),
            selectinload(Appointment.project),
        )
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="预约不存在")
    return _build_appointment_response(appt)


@router.post("/appointments", response_model=AppointmentResponse)
async def create_appointment(
    data: AppointmentCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a new appointment with conflict check."""
    start_t = _parse_time(data.start_time)
    end_minutes = _time_to_minutes(start_t) + data.duration
    end_t = time(end_minutes // 60, end_minutes % 60)

    # Check time conflict for staff
    conflict_query = select(Appointment).where(
        Appointment.staff_id == data.staff_id,
        Appointment.appointment_date == data.appointment_date,
        Appointment.status.in_(["pending", "confirmed"]),
    )
    existing = (await db.execute(conflict_query)).scalars().all()
    for ex in existing:
        ex_start = _time_to_minutes(ex.start_time)
        ex_end = ex_start + ex.duration
        new_start = _time_to_minutes(start_t)
        new_end = end_minutes
        if new_start < ex_end and ex_start < new_end:
            raise HTTPException(
                status_code=400,
                detail=f"美容师在该时段已有预约({ex.start_time}~{time(ex_end // 60, ex_end % 60)})"
            )

    # Check daily limit
    settings = await _get_settings(db, shop_id)
    if settings:
        day_count = await db.execute(
            select(func.count()).select_from(Appointment).where(
                Appointment.staff_id == data.staff_id,
                Appointment.appointment_date == data.appointment_date,
                Appointment.status.in_(["pending", "confirmed", "arrived"]),
            )
        )
        if day_count.scalar() >= settings.max_appointments_per_staff:
            raise HTTPException(status_code=400, detail="美容师当日预约已达上限")

    initial_status = "confirmed" if (settings and settings.auto_confirm) else "pending"

    appointment = Appointment(
        customer_id=data.customer_id, staff_id=data.staff_id,
        shop_id=shop_ids[0], room_id=data.room_id,
        project_id=data.project_id, project_ids=data.project_ids,
        appointment_date=data.appointment_date,
        start_time=start_t, duration=data.duration,
        remark=data.remark, source=data.source,
        status=initial_status,
    )
    if initial_status == "confirmed":
        appointment.confirmed_at = datetime.utcnow()

    db.add(appointment)
    await db.flush()

    # Re-query with eager loading
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment.id)
        .options(
            selectinload(Appointment.customer), selectinload(Appointment.staff),
            selectinload(Appointment.room), selectinload(Appointment.project),
        )
    )
    appointment = result.scalar_one()
    return _build_appointment_response(appointment)


@router.post("/appointments/batch", response_model=MessageResponse)
async def batch_create_appointments(
    data: AppointmentBatchCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Batch create appointments."""
    created_ids = []
    for item in data.appointments:
        appt = Appointment(
            customer_id=item.customer_id, staff_id=item.staff_id,
            shop_id=shop_ids[0], room_id=item.room_id,
            project_id=item.project_id, project_ids=item.project_ids,
            appointment_date=item.appointment_date,
            start_time=_parse_time(item.start_time),
            duration=item.duration, remark=item.remark,
            source=item.source, status="pending",
        )
        db.add(appt)
        await db.flush()
        created_ids.append(str(appt.id))

    return MessageResponse(message=f"批量创建成功，共{len(created_ids)}条", data={"ids": created_ids})


@router.put("/appointments/{appointment_id}", response_model=MessageResponse)
async def update_appointment(
    appointment_id: UUID,
    data: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update appointment info."""
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="预约不存在")
    if appt.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="已完成或已取消的预约不可修改")

    update_data = data.model_dump(exclude_unset=True)
    if "start_time" in update_data and update_data["start_time"]:
        update_data["start_time"] = _parse_time(update_data["start_time"])
    for field, value in update_data.items():
        setattr(appt, field, value)
    db.add(appt)
    return MessageResponse(message="更新成功")


@router.put("/appointments/{appointment_id}/status", response_model=AppointmentResponse)
async def update_appointment_status(
    appointment_id: UUID,
    data: AppointmentStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update appointment status with state machine validation."""
    result = await db.execute(
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .options(
            selectinload(Appointment.customer), selectinload(Appointment.staff),
            selectinload(Appointment.room), selectinload(Appointment.project),
        )
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="预约不存在")

    # State machine validation
    valid_transitions = {
        "pending": ["confirmed", "cancelled"],
        "confirmed": ["arrived", "completed", "cancelled"],
        "arrived": ["completed", "cancelled"],
        "completed": [],
        "cancelled": [],
    }
    allowed = valid_transitions.get(appt.status, [])
    if data.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"不可从 {appt.status} 转为 {data.status}，允许: {allowed}"
        )

    # Cancel time check
    if data.status == "cancelled":
        settings = await _get_settings(db, appt.shop_id)
        if settings and settings.min_cancel_hours > 0:
            appt_datetime = datetime.combine(appt.appointment_date, appt.start_time)
            cancel_deadline = appt_datetime - timedelta(hours=settings.min_cancel_hours)
            if datetime.utcnow() > cancel_deadline:
                raise HTTPException(
                    status_code=400,
                    detail=f"最晚需在预约前{settings.min_cancel_hours}小时取消"
                )
        appt.cancel_reason = data.cancel_reason
        appt.cancelled_at = datetime.utcnow()

    appt.status = data.status
    now = datetime.utcnow()
    if data.status == "confirmed":
        appt.confirmed_at = now
    elif data.status == "arrived":
        appt.arrived_at = now
    elif data.status == "completed":
        appt.completed_at = now

    db.add(appt)
    return _build_appointment_response(appt)


@router.delete("/appointments/{appointment_id}", response_model=MessageResponse)
async def delete_appointment(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Cancel appointment (soft delete via status)."""
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="预约不存在")
    if appt.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="已完成或已取消的预约")
    appt.status = "cancelled"
    appt.cancelled_at = datetime.utcnow()
    db.add(appt)
    return MessageResponse(message="取消成功")


# ============ TimeSlotOccupy ============

@router.get("/occupies", response_model=list[TimeSlotOccupyResponse])
async def list_occupies(
    date: date = Query(...),
    staff_id: Optional[UUID] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List time slot occupies for a date."""
    query = select(TimeSlotOccupy).where(
        TimeSlotOccupy.shop_id.in_(shop_ids),
        TimeSlotOccupy.occupy_date == date,
    )
    if staff_id:
        query = query.where(TimeSlotOccupy.staff_id == staff_id)
    result = await db.execute(query.order_by(TimeSlotOccupy.start_time))
    occupies = result.scalars().all()

    items = []
    for o in occupies:
        items.append(TimeSlotOccupyResponse(
            id=o.id, staff_id=o.staff_id, staff_name=None,
            occupy_date=o.occupy_date,
            start_time=str(o.start_time), end_time=str(o.end_time),
            reason=o.reason, color=o.color, created_at=o.created_at,
        ))
    return items


@router.post("/occupies", response_model=TimeSlotOccupyResponse)
async def create_occupy(
    data: TimeSlotOccupyCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a time slot occupy."""
    occupy = TimeSlotOccupy(
        staff_id=data.staff_id, shop_id=shop_ids[0],
        occupy_date=data.occupy_date,
        start_time=_parse_time(data.start_time),
        end_time=_parse_time(data.end_time),
        reason=data.reason, color=data.color,
    )
    db.add(occupy)
    await db.flush()
    await db.refresh(occupy)
    return TimeSlotOccupyResponse(
        id=occupy.id, staff_id=occupy.staff_id, staff_name=None,
        occupy_date=occupy.occupy_date,
        start_time=str(occupy.start_time), end_time=str(occupy.end_time),
        reason=occupy.reason, color=occupy.color, created_at=occupy.created_at,
    )


@router.put("/occupies/{occupy_id}", response_model=MessageResponse)
async def update_occupy(
    occupy_id: UUID,
    data: TimeSlotOccupyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a time slot occupy."""
    result = await db.execute(select(TimeSlotOccupy).where(TimeSlotOccupy.id == occupy_id))
    occupy = result.scalar_one_or_none()
    if not occupy:
        raise HTTPException(status_code=404, detail="占位不存在")
    update_data = data.model_dump(exclude_unset=True)
    for field in ("start_time", "end_time"):
        if field in update_data and update_data[field]:
            update_data[field] = _parse_time(update_data[field])
    for field, value in update_data.items():
        setattr(occupy, field, value)
    db.add(occupy)
    return MessageResponse(message="更新成功")


@router.delete("/occupies/{occupy_id}", response_model=MessageResponse)
async def delete_occupy(
    occupy_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a time slot occupy."""
    result = await db.execute(select(TimeSlotOccupy).where(TimeSlotOccupy.id == occupy_id))
    occupy = result.scalar_one_or_none()
    if not occupy:
        raise HTTPException(status_code=404, detail="占位不存在")
    await db.delete(occupy)
    return MessageResponse(message="清除成功")


# ============ Appointment Settings ============

async def _get_settings(db: AsyncSession, shop_id: UUID) -> AppointmentSetting | None:
    """Get or create appointment settings for a shop."""
    result = await db.execute(
        select(AppointmentSetting).where(AppointmentSetting.shop_id.in_(shop_ids))
    )
    return result.scalar_one_or_none()


@router.get("/appointment-settings", response_model=AppointmentSettingResponse)
async def get_appointment_settings(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get appointment settings."""
    settings = await _get_settings(db, shop_id)
    if not settings:
        # Create default settings
        settings = AppointmentSetting(shop_id=shop_ids[0])
        db.add(settings)
        await db.flush()
        await db.refresh(settings)
    return AppointmentSettingResponse.model_validate(settings)


@router.put("/appointment-settings", response_model=MessageResponse)
async def update_appointment_settings(
    data: AppointmentSettingUpdate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Update appointment settings."""
    settings = await _get_settings(db, shop_id)
    if not settings:
        settings = AppointmentSetting(shop_id=shop_ids[0])
        db.add(settings)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    db.add(settings)
    return MessageResponse(message="设置已更新")
