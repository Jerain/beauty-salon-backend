"""Attendance router - clock in/out, rules, statistics, approvals."""
from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.attendance import AttendanceRecord, AttendanceRule, AttendanceApprove
from app.models.staff import Staff
from app.schemas.attendance import (
    AttendanceRuleResponse, AttendanceRuleCreate, AttendanceRuleUpdate,
    AttendanceRecordResponse, ClockInRequest, ClockOutRequest,
    AttendanceApproveRequest, AttendanceApproveResponse,
    AttendanceStatisticResponse,
)
from app.schemas.common import MessageResponse
from app.middleware.auth import get_effective_shop_ids, get_current_staff

router = APIRouter(prefix="/api", tags=["考勤管理"])


def _record_response(r: AttendanceRecord) -> AttendanceRecordResponse:
    stf = getattr(r, "staff", None)
    return AttendanceRecordResponse(
        id=r.id,
        staff_id=r.staff_id,
        staff_name=stf.name if stf else None,
        shop_id=r.shop_id,
        record_date=r.record_date,
        clock_in_time=r.clock_in_time,
        clock_out_time=r.clock_out_time,
        status=r.status,
        clock_in_location=r.clock_in_location,
        clock_out_location=r.clock_out_location,
        remark=r.remark,
        created_at=r.created_at,
    )


# ============ Attendance Rule ============

@router.get("/attendance/rule/my", response_model=AttendanceRuleResponse | None)
async def get_my_attendance_rule(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get attendance rule for current shop."""
    result = await db.execute(
        select(AttendanceRule).where(AttendanceRule.shop_id.in_(shop_ids))
    )
    rule = result.scalar_one_or_none()
    return AttendanceRuleResponse.model_validate(rule) if rule else None


@router.post("/attendance/rule", response_model=AttendanceRuleResponse)
async def create_attendance_rule(
    data: AttendanceRuleCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create or update attendance rule for shop."""
    result = await db.execute(
        select(AttendanceRule).where(AttendanceRule.shop_id.in_(shop_ids))
    )
    rule = result.scalar_one_or_none()
    if rule:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)
    else:
        rule = AttendanceRule(shop_id=shop_ids[0], **data.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return AttendanceRuleResponse.model_validate(rule)


@router.put("/attendance/rule/{rule_id}", response_model=AttendanceRuleResponse)
async def update_attendance_rule(
    rule_id: UUID,
    data: AttendanceRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update attendance rule."""
    result = await db.execute(
        select(AttendanceRule).where(AttendanceRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="考勤规则不存在")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return AttendanceRuleResponse.model_validate(rule)


# ============ Clock In/Out ============

@router.post("/attendance/clock-in", response_model=AttendanceRecordResponse)
async def clock_in(
    data: ClockInRequest,
    current_staff: Staff = Depends(get_current_staff),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Clock in for current day."""
    today = date.today()
    # Check if already clocked in today
    result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.staff_id == current_staff.id,
                AttendanceRecord.record_date == today,
            )
        )
    )
    record = result.scalar_one_or_none()
    if record and record.clock_in_time:
        raise HTTPException(status_code=400, detail="今日已打过上班卡")

    now = datetime.utcnow()
    status = "normal"

    # Check late against rule
    rule_result = await db.execute(
        select(AttendanceRule).where(AttendanceRule.shop_id.in_(shop_ids))
    )
    rule = rule_result.scalar_one_or_none()
    if rule:
        start_parts = rule.work_start_time.split(":")
        start_hour, start_min = int(start_parts[0]), int(start_parts[1])
        from datetime import time as dtime
        work_start = datetime(today.year, today.month, today.day, start_hour, start_min)
        late_threshold = timedelta(minutes=rule.late_threshold)
        if now > work_start + late_threshold:
            status = "late"

    if record:
        record.clock_in_time = now
        record.clock_in_location = data.location
        record.status = status
    else:
        record = AttendanceRecord(
            staff_id=current_staff.id,
            shop_id=shop_ids[0],
            record_date=today,
            clock_in_time=now,
            clock_in_location=data.location,
            status=status,
        )
        db.add(record)

    await db.flush()
    await db.refresh(record, ["staff"])
    return _record_response(record)


@router.post("/attendance/clock-out", response_model=AttendanceRecordResponse)
async def clock_out(
    data: ClockOutRequest,
    current_staff: Staff = Depends(get_current_staff),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Clock out for current day."""
    today = date.today()
    result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.staff_id == current_staff.id,
                AttendanceRecord.record_date == today,
            )
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=400, detail="今日未打上班卡")
    if record.clock_out_time:
        raise HTTPException(status_code=400, detail="今日已打过下班卡")

    now = datetime.utcnow()
    record.clock_out_time = now
    record.clock_out_location = data.location

    # Check early leave
    rule_result = await db.execute(
        select(AttendanceRule).where(AttendanceRule.shop_id.in_(shop_ids))
    )
    rule = rule_result.scalar_one_or_none()
    if rule:
        end_parts = rule.work_end_time.split(":")
        end_hour, end_min = int(end_parts[0]), int(end_parts[1])
        work_end = datetime(today.year, today.month, today.day, end_hour, end_min)
        early_threshold = timedelta(minutes=rule.early_leave_threshold)
        if now < work_end - early_threshold and record.status == "normal":
            record.status = "early_leave"

    db.add(record)
    await db.flush()
    await db.refresh(record, ["staff"])
    return _record_response(record)


# ============ Attendance Records ============

@router.get("/attendance/records", response_model=list[AttendanceRecordResponse])
async def list_attendance_records(
    start_date: date = Query(...),
    end_date: date = Query(...),
    staff_id: Optional[UUID] = None,
    current_staff: Staff = Depends(get_current_staff),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List attendance records with date range."""
    query = (
        select(AttendanceRecord)
        .where(
            and_(
                AttendanceRecord.shop_id.in_(shop_ids),
                AttendanceRecord.record_date >= start_date,
                AttendanceRecord.record_date <= end_date,
            )
        )
        .options(selectinload(AttendanceRecord.staff))
    )
    if staff_id:
        query = query.where(AttendanceRecord.staff_id == staff_id)
    query = query.order_by(AttendanceRecord.record_date.desc())
    result = await db.execute(query)
    records = result.scalars().all()
    return [_record_response(r) for r in records]


@router.get("/attendance/my-records", response_model=list[AttendanceRecordResponse])
async def get_my_records(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get current staff's attendance records."""
    result = await db.execute(
        select(AttendanceRecord)
        .where(
            and_(
                AttendanceRecord.staff_id == current_staff.id,
                AttendanceRecord.record_date >= start_date,
                AttendanceRecord.record_date <= end_date,
            )
        )
        .options(selectinload(AttendanceRecord.staff))
        .order_by(AttendanceRecord.record_date.desc())
    )
    records = result.scalars().all()
    return [_record_response(r) for r in records]


# ============ Attendance Statistics ============

@router.get("/attendance/statistic/list", response_model=list[AttendanceStatisticResponse])
async def attendance_statistic_list(
    month: str = Query(..., description="YYYY-MM"),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get attendance statistics for all staff in a month."""
    # Get all active staff
    staff_result = await db.execute(
        select(Staff).where(and_(Staff.shop_id.in_(shop_ids), Staff.is_active == True))
    )
    staff_list = staff_result.scalars().all()

    year, mon = int(month[:4]), int(month[5:7])
    first_day = date(year, mon, 1)
    if mon == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, mon + 1, 1) - timedelta(days=1)
    import calendar
    work_days = calendar.monthrange(year, mon)[1]  # simplified

    stats = []
    for s in staff_list:
        rec_result = await db.execute(
            select(AttendanceRecord).where(
                and_(
                    AttendanceRecord.staff_id == s.id,
                    AttendanceRecord.record_date >= first_day,
                    AttendanceRecord.record_date <= last_day,
                )
            )
        )
        records = rec_result.scalars().all()
        actual = len(records)
        late = sum(1 for r in records if r.status == "late")
        early = sum(1 for r in records if r.status == "early_leave")
        absent = sum(1 for r in records if r.status == "absent")

        stats.append(AttendanceStatisticResponse(
            staff_id=s.id,
            staff_name=s.name,
            month=month,
            work_days=work_days,
            actual_days=actual,
            late_count=late,
            early_leave_count=early,
            absent_count=absent,
        ))
    return stats


@router.get("/attendance/statistic/staff/{staff_id}", response_model=AttendanceStatisticResponse)
async def attendance_statistic_staff(
    staff_id: UUID,
    month: str = Query(..., description="YYYY-MM"),
    db: AsyncSession = Depends(get_db),
):
    """Get attendance statistics for a specific staff."""
    staff_result = await db.execute(select(Staff).where(Staff.id == staff_id))
    s = staff_result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="员工不存在")

    year, mon = int(month[:4]), int(month[5:7])
    first_day = date(year, mon, 1)
    if mon == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, mon + 1, 1) - timedelta(days=1)
    import calendar
    work_days = calendar.monthrange(year, mon)[1]

    rec_result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.staff_id == staff_id,
                AttendanceRecord.record_date >= first_day,
                AttendanceRecord.record_date <= last_day,
            )
        )
    )
    records = rec_result.scalars().all()
    actual = len(records)
    late = sum(1 for r in records if r.status == "late")
    early = sum(1 for r in records if r.status == "early_leave")
    absent = sum(1 for r in records if r.status == "absent")

    return AttendanceStatisticResponse(
        staff_id=s.id,
        staff_name=s.name,
        month=month,
        work_days=work_days,
        actual_days=actual,
        late_count=late,
        early_leave_count=early,
        absent_count=absent,
    )


# ============ Attendance Approval ============

@router.post("/attendance/approve/create", response_model=AttendanceApproveResponse)
async def create_approve(
    data: AttendanceApproveRequest,
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Submit attendance adjustment approval."""
    rec_result = await db.execute(
        select(AttendanceRecord).where(AttendanceRecord.id == data.record_id)
    )
    record = rec_result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="考勤记录不存在")

    approve = AttendanceApprove(
        record_id=data.record_id,
        staff_id=current_staff.id,
        reason=data.reason,
        adjust_type=data.adjust_type,
        adjust_remark=data.adjust_remark,
    )
    db.add(approve)
    await db.flush()
    await db.refresh(approve)
    return AttendanceApproveResponse.model_validate(approve)


@router.get("/attendance/approve/list", response_model=list[AttendanceApproveResponse])
async def list_approves(
    status: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List attendance approvals."""
    query = (
        select(AttendanceApprove)
        .join(AttendanceRecord, AttendanceApprove.record_id == AttendanceRecord.id)
        .where(AttendanceRecord.shop_id.in_(shop_ids))
    )
    if status:
        query = query.where(AttendanceApprove.status == status)
    query = query.order_by(AttendanceApprove.created_at.desc())
    result = await db.execute(query)
    approves = result.scalars().all()
    return [AttendanceApproveResponse.model_validate(a) for a in approves]


@router.put("/attendance/approve/{approve_id}/handle", response_model=MessageResponse)
async def handle_approve(
    approve_id: UUID,
    action: str = Query(..., description="approve/reject"),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject attendance adjustment."""
    result = await db.execute(
        select(AttendanceApprove).where(AttendanceApprove.id == approve_id)
    )
    approve = result.scalar_one_or_none()
    if not approve:
        raise HTTPException(status_code=404, detail="审批记录不存在")

    if action == "approve":
        approve.status = "approved"
        # Update the record status to normal
        rec_result = await db.execute(
            select(AttendanceRecord).where(AttendanceRecord.id == approve.record_id)
        )
        record = rec_result.scalar_one_or_none()
        if record:
            record.status = "normal"
            if approve.adjust_remark:
                record.remark = approve.adjust_remark
            db.add(record)
    else:
        approve.status = "rejected"

    db.add(approve)
    return MessageResponse(message=f"{'审批通过' if action == 'approve' else '审批拒绝'}")
