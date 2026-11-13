"""Revisit router - tasks, records, scripts, service logs, target plans."""
import json
from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.revisit import RevisitTask, RevisitRecord, ServiceLog, RevisitScript, TargetPlan
from app.models.staff import Staff
from app.models.customer import Customer
from app.schemas.revisit import (
    RevisitTaskResponse, RevisitTaskCreate, RevisitTaskUpdate,
    RevisitRecordResponse, RevisitRecordCreate,
    RevisitStatisticResponse, ServiceLogResponse, ServiceLogCreate,
    RevisitScriptResponse, RevisitScriptCreate,
    TargetPlanResponse, TargetPlanCreate,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.middleware.auth import get_effective_shop_ids, get_current_staff

router = APIRouter(prefix="/api", tags=["回访与服务日志"])


def _task_response(t: RevisitTask) -> RevisitTaskResponse:
    cust = getattr(t, "customer", None)
    stf = getattr(t, "staff", None)
    return RevisitTaskResponse(
        id=t.id, customer_id=t.customer_id,
        customer_name=cust.name if cust else None,
        staff_id=t.staff_id, staff_name=stf.name if stf else None,
        shop_id=t.shop_id, revisit_type=t.revisit_type,
        planned_date=t.planned_date, content=t.content,
        status=t.status, priority=t.priority, created_at=t.created_at,
    )


def _record_response(r: RevisitRecord) -> RevisitRecordResponse:
    cust = getattr(r, "customer", None)
    stf = getattr(r, "staff", None)
    return RevisitRecordResponse(
        id=r.id, task_id=r.task_id, customer_id=r.customer_id,
        customer_name=cust.name if cust else None,
        staff_id=r.staff_id, staff_name=stf.name if stf else None,
        revisit_method=r.revisit_method, result=r.result,
        content=r.content, next_plan=r.next_plan, created_at=r.created_at,
    )


def _log_response(l: ServiceLog) -> ServiceLogResponse:
    cust = getattr(l, "customer", None)
    stf = getattr(l, "staff", None)
    before = json.loads(l.before_images) if l.before_images else None
    after = json.loads(l.after_images) if l.after_images else None
    return ServiceLogResponse(
        id=l.id, customer_id=l.customer_id,
        customer_name=cust.name if cust else None,
        staff_id=l.staff_id, staff_name=stf.name if stf else None,
        shop_id=l.shop_id, order_id=l.order_id, project_id=l.project_id,
        service_date=l.service_date, duration=l.duration,
        before_images=before, after_images=after,
        remark=l.remark, customer_feedback=l.customer_feedback,
        status=l.status, created_at=l.created_at,
    )


# ============ Revisit Tasks ============

@router.get("/revisit-tasks", response_model=PaginatedResponse[RevisitTaskResponse])
async def list_revisit_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    revisit_type: Optional[str] = None,
    staff_id: Optional[UUID] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(RevisitTask).where(RevisitTask.shop_id.in_(shop_ids))
        .options(selectinload(RevisitTask.customer), selectinload(RevisitTask.staff))
    )
    if status:
        query = query.where(RevisitTask.status == status)
    if revisit_type:
        query = query.where(RevisitTask.revisit_type == revisit_type)
    if staff_id:
        query = query.where(RevisitTask.staff_id == staff_id)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(RevisitTask.planned_date.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tasks = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[_task_response(t) for t in tasks],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.post("/revisit-tasks", response_model=RevisitTaskResponse)
async def create_revisit_task(
    data: RevisitTaskCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    task = RevisitTask(
        customer_id=data.customer_id, staff_id=data.staff_id,
        shop_id=shop_ids[0], revisit_type=data.revisit_type,
        planned_date=data.planned_date, content=data.content,
        priority=data.priority,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task, ["customer", "staff"])
    return _task_response(task)


# ============ Revisit Statistics (MUST be before {task_id}) ============

@router.get("/revisit-tasks/statistic", response_model=RevisitStatisticResponse)
async def revisit_statistic(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    base = select(RevisitTask).where(RevisitTask.shop_id.in_(shop_ids))
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    pending = (await db.execute(
        select(func.count()).select_from(base.where(RevisitTask.status == "pending").subquery())
    )).scalar() or 0
    completed = (await db.execute(
        select(func.count()).select_from(base.where(RevisitTask.status == "completed").subquery())
    )).scalar() or 0
    cancelled = (await db.execute(
        select(func.count()).select_from(base.where(RevisitTask.status == "cancelled").subquery())
    )).scalar() or 0
    expired = (await db.execute(
        select(func.count()).select_from(base.where(RevisitTask.status == "expired").subquery())
    )).scalar() or 0
    rate = (completed / total * 100) if total > 0 else 0.0
    return RevisitStatisticResponse(
        total_tasks=total, pending_count=pending, completed_count=completed,
        cancelled_count=cancelled, expired_count=expired, completion_rate=round(rate, 1),
    )


@router.get("/revisit-tasks/{task_id}", response_model=RevisitTaskResponse)
async def get_revisit_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RevisitTask).where(RevisitTask.id == task_id)
        .options(selectinload(RevisitTask.customer), selectinload(RevisitTask.staff))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="回访任务不存在")
    return _task_response(task)


@router.put("/revisit-tasks/{task_id}", response_model=RevisitTaskResponse)
async def update_revisit_task(
    task_id: UUID, data: RevisitTaskUpdate, db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RevisitTask).where(RevisitTask.id == task_id)
        .options(selectinload(RevisitTask.customer), selectinload(RevisitTask.staff))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="回访任务不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.add(task)
    await db.flush()
    await db.refresh(task, ["customer", "staff"])
    return _task_response(task)


@router.put("/revisit-tasks/{task_id}/cancel", response_model=MessageResponse)
async def cancel_revisit_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RevisitTask).where(RevisitTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="回访任务不存在")
    task.status = "cancelled"
    db.add(task)
    return MessageResponse(message="已取消")


# ============ Revisit Records ============

@router.post("/revisit-records", response_model=RevisitRecordResponse)
async def create_revisit_record(
    data: RevisitRecordCreate,
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    record = RevisitRecord(
        task_id=data.task_id, customer_id=data.customer_id,
        staff_id=current_staff.id, revisit_method=data.revisit_method,
        result=data.result, content=data.content, next_plan=data.next_plan,
    )
    db.add(record)
    # If linked task, mark as completed
    if data.task_id:
        task_result = await db.execute(
            select(RevisitTask).where(RevisitTask.id == data.task_id)
        )
        task = task_result.scalar_one_or_none()
        if task:
            task.status = "completed"
            db.add(task)
    await db.flush()
    await db.refresh(record, ["customer", "staff"])
    return _record_response(record)


@router.get("/revisit-records", response_model=list[RevisitRecordResponse])
async def list_revisit_records(
    customer_id: Optional[UUID] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(RevisitRecord)
        .join(Customer, RevisitRecord.customer_id == Customer.id)
        .where(Customer.shop_id.in_(shop_ids))
        .options(selectinload(RevisitRecord.customer), selectinload(RevisitRecord.staff))
    )
    if customer_id:
        query = query.where(RevisitRecord.customer_id == customer_id)
    query = query.order_by(RevisitRecord.created_at.desc())
    result = await db.execute(query)
    return [_record_response(r) for r in result.scalars().all()]


# ============ Revisit Scripts ============

@router.get("/revisit-scripts", response_model=list[RevisitScriptResponse])
async def list_revisit_scripts(
    category: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    query = select(RevisitScript).where(
        and_(RevisitScript.is_active == True, RevisitScript.shop_id.in_(shop_ids))
    )
    if category:
        query = query.where(RevisitScript.category == category)
    result = await db.execute(query.order_by(RevisitScript.created_at.desc()))
    return [RevisitScriptResponse.model_validate(s) for s in result.scalars().all()]


@router.post("/revisit-scripts", response_model=RevisitScriptResponse)
async def create_revisit_script(
    data: RevisitScriptCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    script = RevisitScript(
        title=data.title, category=data.category,
        content=data.content, scenario=data.scenario, shop_id=shop_ids[0],
    )
    db.add(script)
    await db.flush()
    await db.refresh(script)
    return RevisitScriptResponse.model_validate(script)


@router.delete("/revisit-scripts/{script_id}", response_model=MessageResponse)
async def delete_revisit_script(script_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RevisitScript).where(RevisitScript.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="话术不存在")
    script.is_active = False
    db.add(script)
    return MessageResponse(message="删除成功")


# ============ Service Logs ============

@router.get("/service-logs", response_model=PaginatedResponse[ServiceLogResponse])
async def list_service_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: Optional[UUID] = None,
    staff_id: Optional[UUID] = None,
    view_mode: str = Query("log", description="log/order"),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(ServiceLog).where(ServiceLog.shop_id.in_(shop_ids))
        .options(selectinload(ServiceLog.customer), selectinload(ServiceLog.staff))
    )
    if customer_id:
        query = query.where(ServiceLog.customer_id == customer_id)
    if staff_id:
        query = query.where(ServiceLog.staff_id == staff_id)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(ServiceLog.service_date.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[_log_response(l) for l in logs],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.post("/service-logs", response_model=ServiceLogResponse)
async def create_service_log(
    data: ServiceLogCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    log = ServiceLog(
        customer_id=data.customer_id, staff_id=data.staff_id,
        shop_id=shop_ids[0], order_id=data.order_id, project_id=data.project_id,
        service_date=data.service_date, duration=data.duration,
        before_images=json.dumps(data.before_images) if data.before_images else None,
        after_images=json.dumps(data.after_images) if data.after_images else None,
        remark=data.remark, customer_feedback=data.customer_feedback,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log, ["customer", "staff"])
    return _log_response(log)


@router.get("/service-logs/{log_id}", response_model=ServiceLogResponse)
async def get_service_log(log_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ServiceLog).where(ServiceLog.id == log_id)
        .options(selectinload(ServiceLog.customer), selectinload(ServiceLog.staff))
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="服务日志不存在")
    return _log_response(log)


# ============ Target Plans ============

@router.get("/target-plans", response_model=list[TargetPlanResponse])
async def list_target_plans(
    month: str = Query(..., description="YYYY-MM"),
    target_type: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(TargetPlan).where(
            and_(TargetPlan.shop_id.in_(shop_ids), TargetPlan.month == month)
        ).options(selectinload(TargetPlan.staff))
    )
    if target_type:
        query = query.where(TargetPlan.target_type == target_type)
    result = await db.execute(query.order_by(TargetPlan.created_at.desc()))
    plans = result.scalars().all()
    return [
        TargetPlanResponse(
            id=p.id, shop_id=p.shop_id, target_type=p.target_type,
            target_value=float(p.target_value), actual_value=float(p.actual_value),
            completion_rate=round(float(p.actual_value) / float(p.target_value) * 100, 1) if float(p.target_value) > 0 else 0.0,
            month=p.month,
            staff_id=p.staff_id,
            staff_name=p.staff.name if p.staff else None,
            created_at=p.created_at,
        )
        for p in plans
    ]


@router.post("/target-plans", response_model=TargetPlanResponse)
async def create_target_plan(
    data: TargetPlanCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    plan = TargetPlan(
        shop_id=shop_ids[0], target_type=data.target_type,
        target_value=data.target_value, month=data.month,
        staff_id=data.staff_id,
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan, ["staff"])
    return TargetPlanResponse(
        id=plan.id, shop_id=plan.shop_id, target_type=plan.target_type,
        target_value=float(plan.target_value), actual_value=float(plan.actual_value),
        completion_rate=0.0, month=plan.month,
        staff_id=plan.staff_id,
        staff_name=plan.staff.name if plan.staff else None,
        created_at=plan.created_at,
    )


@router.delete("/target-plans/{plan_id}", response_model=MessageResponse)
async def delete_target_plan(plan_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TargetPlan).where(TargetPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="目标计划不存在")
    await db.delete(plan)
    return MessageResponse(message="删除成功")
