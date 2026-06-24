from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models_sql import ParentChild, Member   # FIXED IMPORT

router = APIRouter(prefix="/parentchild", tags=["parentchild"])


# ---------------- SCHEMA (Pydantic) ----------------
from pydantic import BaseModel


class ParentChildCreate(BaseModel):
    parentId: str
    childId: str


class ParentChildOut(ParentChildCreate):
    id: str

    class Config:
        from_attributes = True


# ---------------- GET ALL ----------------
@router.get("/", response_model=List[ParentChildOut])
async def get_parentchild(db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(ParentChild))
    return result.scalars().all()


# ---------------- ADD RELATION ----------------
@router.post("/", response_model=ParentChildOut)
async def add_parentchild(rel: ParentChildCreate, db: AsyncSession = Depends(get_db)):

    # check existing relation
    result = await db.execute(
        select(ParentChild).where(
            ParentChild.parentId == rel.parentId,
            ParentChild.childId == rel.childId
        )
    )

    existing = result.scalars().first()

    if existing:
        raise HTTPException(status_code=400, detail="Relation already exists")

    # create relation
    new_rel = ParentChild(
        id=str(uuid4()),
        parentId=rel.parentId,
        childId=rel.childId
    )

    db.add(new_rel)

    # update parent
    result = await db.execute(
        select(Member).where(Member.id == rel.parentId)
    )
    parent = result.scalars().first()

    if parent:
        parent.childrenIds = parent.childrenIds or []
        if rel.childId not in parent.childrenIds:
            parent.childrenIds.append(rel.childId)

    # update child
    result = await db.execute(
        select(Member).where(Member.id == rel.childId)
    )
    child = result.scalars().first()

    if child:
        child.parentIds = child.parentIds or []
        if rel.parentId not in child.parentIds:
            child.parentIds.append(rel.parentId)

    await db.commit()

    return new_rel