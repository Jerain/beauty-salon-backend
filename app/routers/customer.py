"""Customer router - CRUD + tags + sources."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.customer import Customer, Tag, Source, CustomerTag
from app.schemas.customer import (
    CustomerCreate, CustomerUpdate, CustomerResponse, CustomerListResponse,
    TagCreate, TagResponse, SourceCreate, SourceResponse,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.middleware.auth import get_effective_shop_ids, get_current_staff
from app.models.staff import Staff

router = APIRouter(prefix="/api", tags=["顾客管理"])

# ========== Pinyin Helper ==========
# Comprehensive GB2312 pinyin lookup: (gb_code_threshold, pinyin_string)
# Sorted ascending by gb_code. For each character, find the last entry where gb_code >= threshold.
_PINYIN_GB = [
    (0xB0A1, 'a'), (0xB0C5, 'ai'), (0xB2C1, 'an'), (0xB2C9, 'ang'),
    (0xB2E3, 'ao'), (0xB2E7, 'ba'), (0xB3A3, 'bai'), (0xB3EC, 'ban'),
    (0xB4A9, 'bang'), (0xB4D4, 'bao'), (0xB5A2, 'bei'), (0xB5B6, 'ben'),
    (0xB5C8, 'beng'), (0xB5E5, 'bi'), (0xB6A1, 'bian'), (0xB6B9, 'biao'),
    (0xB6E0, 'bie'), (0xB6EC, 'bin'), (0xB7A2, 'bing'), (0xB7B0, 'bo'),
    (0xB7C1, 'bu'), (0xB8C1, 'ca'), (0xB8CA, 'cai'), (0xB8D5, 'can'),
    (0xB8ED, 'cang'), (0xB8F3, 'cao'), (0xB8FC, 'ce'), (0xB9A2, 'ceng'),
    (0xB9B2, 'cha'), (0xB9B8, 'chai'), (0xB9BD, 'chan'), (0xB9E4, 'chang'),
    (0xB9F6, 'chao'), (0xBAA3, 'che'), (0xBAA8, 'chen'), (0xBAB0, 'cheng'),
    (0xBAC4, 'chi'), (0xBAD0, 'chong'), (0xBAD8, 'chou'), (0xBAF0, 'chu'),
    (0xBBF7, 'chuai'), (0xBBFA, 'chuan'), (0xBCA2, 'chuang'), (0xBCAB, 'chui'),
    (0xBCB5, 'chun'), (0xBCD0, 'chuo'), (0xBCE5, 'ci'), (0xBCF6, 'cong'),
    (0xBDAB, 'cou'), (0xBDB1, 'cu'), (0xBDD8, 'cuan'), (0xBDE4, 'cui'),
    (0xBDF0, 'cun'), (0xBDFB, 'cuo'), (0xBEA1, 'da'), (0xBEAA, 'dai'),
    (0xBEB0, 'dan'), (0xBEC4, 'dang'), (0xBED2, 'dao'), (0xBEE3, 'de'),
    (0xBEE8, 'deng'), (0xBEF9, 'di'), (0xBFA1, 'dian'), (0xBFA9, 'diao'),
    (0xBFB8, 'die'), (0xBFC5, 'ding'), (0xBFD2, 'diu'), (0xBFDB, 'dong'),
    (0xBFE4, 'dou'), (0xBFF5, 'du'), (0xC0A1, 'duan'), (0xC0AC, 'dui'),
    (0xC0B5, 'dun'), (0xC0C6, 'duo'), (0xC0D2, 'e'), (0xC0E3, 'en'),
    (0xC0EC, 'er'), (0xC0F4, 'fa'), (0xC1AC, 'fan'), (0xC1CA, 'fang'),
    (0xC1DB, 'fei'), (0xC1EC, 'fen'), (0xC1FD, 'feng'), (0xC2A5, 'fo'),
    (0xC2A8, 'fou'), (0xC2AB, 'fu'), (0xC2E8, 'ga'), (0xC2F4, 'gai'),
    (0xC3A1, 'gan'), (0xC3B4, 'gang'), (0xC3CA, 'gao'), (0xC3DB, 'ge'),
    (0xC3F2, 'gei'), (0xC3F5, 'gen'), (0xC3FC, 'geng'), (0xC4A3, 'gong'),
    (0xC4B0, 'gou'), (0xC4BA, 'gu'), (0xC4CC, 'gua'), (0xC4DA, 'guai'),
    (0xC4E4, 'guan'), (0xC4F5, 'guang'), (0xC5A1, 'gui'), (0xC5B6, 'gun'),
    (0xC5BE, 'guo'), (0xC5D2, 'ha'), (0xC5DA, 'hai'), (0xC5E5, 'han'),
    (0xC5F0, 'hang'), (0xC5F6, 'hao'), (0xC6A2, 'he'), (0xC6AC, 'hei'),
    (0xC6B2, 'hen'), (0xC6B8, 'heng'), (0xC6C1, 'hong'), (0xC6CA, 'hou'),
    (0xC6D0, 'hu'), (0xC6DA, 'hua'), (0xC6E2, 'huai'), (0xC6ED, 'huan'),
    (0xC6F8, 'huang'), (0xC7A6, 'hui'), (0xC7B2, 'hun'), (0xC7BA, 'huo'),
    (0xC7C5, 'ji'), (0xC7E0, 'jia'), (0xC8A1, 'jian'), (0xC8B6, 'jiang'),
    (0xC8CB, 'jiao'), (0xC8D5, 'jie'), (0xC8E4, 'jin'), (0xC8F6, 'jing'),
    (0xC9A6, 'jiong'), (0xC9AB, 'jiu'), (0xC9B5, 'ju'), (0xC9C8, 'juan'),
    (0xC9D5, 'jue'), (0xC9E0, 'jun'), (0xC9EA, 'ka'), (0xC9F0, 'kai'),
    (0xC9F8, 'kan'), (0xC9FC, 'kang'), (0xCAAB, 'kao'), (0xCAA4, 'ke'),
    (0xCAB5, 'ken'), (0xCAB9, 'keng'), (0xCABC, 'kong'), (0xCAC4, 'kou'),
    (0xCACB, 'ku'), (0xCAD4, 'kua'), (0xCADD, 'kuai'), (0xCAE3, 'kuan'),
    (0xCAEC, 'kuang'), (0xCAF5, 'kui'), (0xCBAB, 'kun'), (0xCBB0, 'kuo'),
    (0xCBB8, 'la'), (0xCBC0, 'lai'), (0xCBC7, 'lan'), (0xCBDC, 'lang'),
    (0xCBE6, 'lao'), (0xCBF0, 'le'), (0xCBF3, 'lei'), (0xCBFA, 'leng'),
    (0xCCA1, 'li'), (0xCCB6, 'lia'), (0xCCBC, 'lian'), (0xCCD4, 'liang'),
    (0xCCE3, 'liao'), (0xCCF2, 'lie'), (0xCCFA, 'lin'), (0xCDAB, 'ling'),
    (0xCDB2, 'liu'), (0xCDC4, 'long'), (0xCDD0, 'lou'), (0xCDDA, 'lu'),
    (0xCDE5, 'lü'), (0xCDED, 'luan'), (0xCDF5, 'lüe'), (0xCEA1, 'lun'),
    (0xCEA8, 'luo'), (0xCEB5, 'ma'), (0xCEC2, 'mai'), (0xCECC, 'man'),
    (0xCEDA, 'mang'), (0xCEE5, 'mao'), (0xCEF4, 'me'), (0xCEF8, 'mei'),
    (0xCFAB, 'men'), (0xCFB5, 'meng'), (0xCFCA, 'mi'), (0xCFE0, 'mian'),
    (0xCFEC, 'miao'), (0xCFF6, 'mie'), (0xCFFB, 'min'), (0xD0A6, 'ming'),
    (0xD0B2, 'miu'), (0xD0B6, 'mo'), (0xD0C4, 'mou'), (0xD0D2, 'mu'),
    (0xD0DC, 'na'), (0xD0E5, 'nai'), (0xD0F0, 'nan'), (0xD0F6, 'nang'),
    (0xD0FA, 'nao'), (0xD1A1, 'ne'), (0xD1A4, 'nei'), (0xD1A8, 'nen'),
    (0xD1AB, 'neng'), (0xD1B0, 'ni'), (0xD1B9, 'nian'), (0xD1C5, 'niang'),
    (0xD1CC, 'niao'), (0xD1D2, 'nie'), (0xD1DA, 'nin'), (0xD1E1, 'ning'),
    (0xD1EA, 'niu'), (0xD1F0, 'nong'), (0xD1F5, 'nu'), (0xD1FA, 'nü'),
    (0xD2A1, 'nuan'), (0xD2A8, 'nüe'), (0xD2AB, 'nuo'), (0xD2B2, 'o'),
    (0xD2B8, 'ou'), (0xD2C1, 'pa'), (0xD2CA, 'pai'), (0xD2D4, 'pan'),
    (0xD2DE, 'pang'), (0xD2E8, 'pao'), (0xD2F0, 'pei'), (0xD2F8, 'pen'),
    (0xD2FC, 'peng'), (0xD3A6, 'pi'), (0xD3B2, 'pian'), (0xD3BC, 'piao'),
    (0xD3C5, 'pie'), (0xD3CA, 'pin'), (0xD3D4, 'ping'), (0xD3E0, 'po'),
    (0xD3EA, 'pu'), (0xD3F4, 'qi'), (0xD4A8, 'qia'), (0xD4B0, 'qian'),
    (0xD4C8, 'qiang'), (0xD4D1, 'qiao'), (0xD4E2, 'qie'), (0xD4EC, 'qin'),
    (0xD4F5, 'qing'), (0xD5A6, 'qiong'), (0xD5AB, 'qiu'), (0xD5B5, 'qu'),
    (0xD5C0, 'quan'), (0xD5D0, 'que'), (0xD5DA, 'qun'), (0xD5E0, 'ran'),
    (0xD5E8, 'rang'), (0xD5EE, 'rao'), (0xD5F2, 're'), (0xD5F8, 'ren'),
    (0xD6A2, 'reng'), (0xD6A6, 'ri'), (0xD6AA, 'rong'), (0xD6B5, 'rou'),
    (0xD6BE, 'ru'), (0xD6C8, 'ruan'), (0xD6D0, 'rui'), (0xD6D5, 'run'),
    (0xD6DA, 'ruo'), (0xD6E0, 'sa'), (0xD6E4, 'sai'), (0xD6E8, 'san'),
    (0xD6EC, 'sang'), (0xD6F0, 'sao'), (0xD6F4, 'se'), (0xD6F8, 'sen'),
    (0xD6FA, 'seng'), (0xD6FC, 'sha'), (0xD7A2, 'shai'), (0xD7A8, 'shan'),
    (0xD7B8, 'shang'), (0xD7C6, 'shao'), (0xD7D2, 'she'), (0xD7DA, 'shen'),
    (0xD7E8, 'sheng'), (0xD8A2, 'shi'), (0xD8B8, 'shou'), (0xD8C4, 'shu'),
    (0xD8D8, 'shua'), (0xD8DE, 'shuai'), (0xD8E6, 'shuan'), (0xD8EC, 'shuang'),
    (0xD8F2, 'shui'), (0xD8FA, 'shun'), (0xD9A2, 'shuo'), (0xD9A8, 'si'),
    (0xD9B4, 'song'), (0xD9BE, 'sou'), (0xD9C4, 'su'), (0xD9CE, 'suan'),
    (0xD9D6, 'sui'), (0xD9DE, 'sun'), (0xD9E4, 'suo'), (0xD9EC, 'ta'),
    (0xD9F2, 'tai'), (0xD9FA, 'tan'), (0xDAA6, 'tang'), (0xDAB6, 'tao'),
    (0xDAC0, 'te'), (0xDAC4, 'teng'), (0xDACA, 'ti'), (0xDAD4, 'tian'),
    (0xDAE0, 'tiao'), (0xDAEA, 'tie'), (0xDAF0, 'ting'), (0xDAFA, 'tong'),
    (0xDBA8, 'tou'), (0xDBB0, 'tu'), (0xDBB8, 'tuan'), (0xDBC0, 'tui'),
    (0xDBC8, 'tun'), (0xDBD0, 'tuo'), (0xDBDA, 'wa'), (0xDBE0, 'wai'),
    (0xDBE6, 'wan'), (0xDBF0, 'wang'), (0xDBFC, 'wei'), (0xDCA8, 'wen'),
    (0xDCB4, 'weng'), (0xDCBC, 'wo'), (0xDCCA, 'wu'), (0xDCDA, 'xi'),
    (0xDCE8, 'xia'), (0xDCFA, 'xian'), (0xDDAB, 'xiang'), (0xDDB8, 'xiao'),
    (0xDDC8, 'xie'), (0xDDE0, 'xin'), (0xDDEC, 'xing'), (0xDDF6, 'xiong'),
    (0xDEA1, 'xiu'), (0xDEAC, 'xu'), (0xDEC0, 'xuan'), (0xDED0, 'xue'),
    (0xDEDA, 'xun'), (0xDEE4, 'ya'), (0xDEFA, 'yan'), (0xDFAA, 'yang'),
    (0xDFB8, 'yao'), (0xDFC6, 'ye'), (0xDFD0, 'yi'), (0xDFE0, 'yin'),
    (0xDFEE, 'ying'), (0xDFFA, 'yo'), (0xDFFD, 'yong'), (0xE0A1, 'you'),
    (0xE0B0, 'yu'), (0xE0C0, 'yuan'), (0xE0D4, 'yue'), (0xE0E0, 'yun'),
    (0xE0EC, 'za'), (0xE0F0, 'zai'), (0xE0F6, 'zan'), (0xE0FC, 'zang'),
    (0xE1A4, 'zao'), (0xE1AE, 'ze'), (0xE1B2, 'zei'), (0xE1B6, 'zen'),
    (0xE1B8, 'zeng'), (0xE1C0, 'zha'), (0xE1CA, 'zhai'), (0xE1D4, 'zhan'),
    (0xE1E2, 'zhang'), (0xE1F0, 'zhao'), (0xE1FA, 'zhe'), (0xE2A6, 'zhen'),
    (0xE2B4, 'zheng'), (0xE2C2, 'zhi'), (0xE2D6, 'zhong'), (0xE2E0, 'zhou'),
    (0xE2EC, 'zhu'), (0xE2F6, 'zhua'), (0xE2FA, 'zhuai'), (0xE3A2, 'zhuan'),
    (0xE3AC, 'zhuang'), (0xE3B6, 'zhui'), (0xE3BC, 'zhun'), (0xE3C2, 'zhuo'),
    (0xE3CA, 'zi'), (0xE3D4, 'zong'), (0xE3DC, 'zou'), (0xE3E0, 'zu'),
    (0xE3E6, 'zuan'), (0xE3EC, 'zui'), (0xE3F2, 'zun'), (0xE3F6, 'zuo'),
]

def _to_pinyin(name: str) -> str:
    """Convert Chinese name to pinyin string for sorting."""
    result = []
    for ch in name:
        try:
            gb = ch.encode('gbk')
            if len(gb) == 2:
                code = gb[0] * 256 + gb[1]
                # Binary search for the last entry where code >= threshold
                lo, hi = 0, len(_PINYIN_GB) - 1
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if _PINYIN_GB[mid][0] <= code:
                        lo = mid
                    else:
                        hi = mid - 1
                result.append(_PINYIN_GB[lo][1])
            else:
                result.append(ch.lower() if ch.isalpha() else ch)
        except (UnicodeEncodeError, UnicodeDecodeError):
            result.append(ch.lower() if ch.isalpha() else ch)
    return ''.join(result)


# ============ Customer CRUD ============

@router.get("/customers", response_model=PaginatedResponse[CustomerListResponse])
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    level: Optional[str] = None,
    tag_id: Optional[UUID] = None,
    source_id: Optional[UUID] = None,
    sort_by: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated customer list with search and filters.
    sort_by: 'name' for pinyin sort, default by created_at desc.
    """
    query = (
        select(Customer)
        .where(Customer.shop_id.in_(shop_ids), Customer.is_active == True)
        .options(selectinload(Customer.tags))
    )

    if search:
        query = query.where(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.code.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
            )
        )
    if level:
        query = query.where(Customer.level == level)
    if source_id:
        query = query.where(Customer.source_id == source_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    if sort_by == "name":
        # Fetch all, sort by pinyin in Python, then paginate
        result = await db.execute(query)
        all_customers = result.scalars().all()
        all_customers.sort(key=lambda c: _to_pinyin(c.name))
        start = (page - 1) * page_size
        end = start + page_size
        customers = all_customers[start:end]
    else:
        # Default: order by created_at desc with SQL pagination
        query = query.order_by(Customer.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        customers = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[CustomerListResponse.model_validate(c) for c in customers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/customers", response_model=CustomerResponse)
async def create_customer(
    data: CustomerCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new customer."""
    # Generate customer code
    count_result = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.shop_id.in_(shop_ids))
    )
    count = count_result.scalar() + 1
    code = f"C{count:04d}"

    customer = Customer(
        name=data.name,
        code=code,
        phone=data.phone,
        gender=data.gender,
        birthday=data.birthday,
        shop_id=shop_ids[0],
        source_id=data.source_id,
        staff_id=data.staff_id or current_staff.id,
        level=data.level,
        remark=data.remark,
        taboo=data.taboo,
    )
    db.add(customer)
    await db.flush()
    await db.refresh(customer, ["tags"])

    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        code=customer.code,
        phone=customer.phone,
        gender=customer.gender,
        birthday=customer.birthday,
        avatar_url=customer.avatar_url,
        level=customer.level,
        balance=float(customer.balance),
        points=customer.points,
        total_consumption=float(customer.total_consumption),
        remark=customer.remark,
        taboo=customer.taboo,
        last_visit_at=customer.last_visit_at,
        is_blacklisted=customer.is_blacklisted,
        source_name=None,
        staff_name=None,
        tags=[],
        created_at=customer.created_at,
    )


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get customer detail."""
    result = await db.execute(
        select(Customer)
        .where(Customer.id == customer_id)
        .options(selectinload(Customer.tags), selectinload(Customer.source), selectinload(Customer.responsible_staff))
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="顾客不存在")

    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        code=customer.code,
        phone=customer.phone,
        gender=customer.gender,
        birthday=customer.birthday,
        avatar_url=customer.avatar_url,
        level=customer.level,
        balance=float(customer.balance),
        points=customer.points,
        total_consumption=float(customer.total_consumption),
        remark=customer.remark,
        taboo=customer.taboo,
        last_visit_at=customer.last_visit_at,
        is_blacklisted=customer.is_blacklisted,
        source_name=customer.source.name if customer.source else None,
        staff_name=customer.responsible_staff.name if customer.responsible_staff else None,
        tags=[TagResponse.model_validate(t) for t in customer.tags],
        created_at=customer.created_at,
    )


@router.put("/customers/{customer_id}", response_model=MessageResponse)
async def update_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update customer info."""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="顾客不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    db.add(customer)
    return MessageResponse(message="更新成功")


@router.delete("/customers/{customer_id}", response_model=MessageResponse)
async def delete_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete customer."""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="顾客不存在")

    customer.is_active = False
    db.add(customer)
    return MessageResponse(message="删除成功")


# ============ Tags ============

@router.get("/tags", response_model=list[TagResponse])
async def list_tags(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List all tags for the shop."""
    result = await db.execute(
        select(Tag).where(or_(Tag.shop_id.in_(shop_ids), Tag.shop_id == None), Tag.is_active == True)
    )
    tags = result.scalars().all()
    return [TagResponse.model_validate(t) for t in tags]


@router.post("/tags", response_model=TagResponse)
async def create_tag(
    data: TagCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a new tag."""
    tag = Tag(name=data.name, color=data.color, shop_id=shop_ids[0])
    db.add(tag)
    await db.flush()
    await db.refresh(tag)
    return TagResponse.model_validate(tag)


# ============ Sources ============

@router.get("/sources", response_model=list[SourceResponse])
async def list_sources(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List all sources for the shop."""
    result = await db.execute(
        select(Source).where(or_(Source.shop_id.in_(shop_ids), Source.shop_id == None), Source.is_active == True)
    )
    sources = result.scalars().all()
    return [SourceResponse.model_validate(s) for s in sources]


@router.post("/sources", response_model=SourceResponse)
async def create_source(
    data: SourceCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a new source."""
    source = Source(name=data.name, shop_id=shop_ids[0])
    db.add(source)
    await db.flush()
    await db.refresh(source)
    return SourceResponse.model_validate(source)
