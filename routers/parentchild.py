from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import ParentChild, Relationships, Member

router = APIRouter(prefix="/parentchild", tags=["parentchild"])

# ---------------- GET ALL ----------------
@router.get("/", response_model=List[ParentChild])
async def get_parentchild(db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Relationships).where(Relationships.type == "parentChild")
    )

    return result.scalars().all()


# ---------------- ADD RELATION ----------------
@router.post("/", response_model=ParentChild)
async def add_parentchild(rel: ParentChild, db: AsyncSession = Depends(get_db)):

    # check existing relation
    result = await db.execute(
        select(Relationships).where(
            Relationships.type == "parentChild",
            Relationships.parentId == rel.parentId,
            Relationships.childId == rel.childId
        )
    )

    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Relation already exists")

    # create relation
    new_rel = Relationships(
        type="parentChild",
        parentId=rel.parentId,
        childId=rel.childId
    )

    db.add(new_rel)

    # update parent
    result = await db.execute(
        select(Member).where(Member.id == rel.parentId)
    )
    parent = result.scalar_one_or_none()

    if parent:
        if not parent.childrenIds:
            parent.childrenIds = []
        parent.childrenIds.append(rel.childId)

    # update child
    result = await db.execute(
        select(Member).where(Member.id == rel.childId)
    )
    child = result.scalar_one_or_none()

    if child:
        if not child.parentIds:
            child.parentIds = []
        child.parentIds.append(rel.parentId)

    await db.commit()

    return new_rel