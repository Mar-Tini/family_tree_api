from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4

from database import get_db
from models_sql import ParentChild, Member

from pydantic import BaseModel

router = APIRouter(prefix="/parentchild", tags=["parentchild"])


# ---------------- SCHEMA ----------------
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
        id=str(uuid4()),   # ✅ FIX IMPORTANT
        parentId=rel.parentId,
        childId=rel.childId
    )

    db.add(new_rel)

    # ---------------- UPDATE PARENT ----------------
    result = await db.execute(
        select(Member).where(Member.id == rel.parentId)
    )
    parent = result.scalars().first()

    if parent:
        current = parent.childrenIds or []

        if not isinstance(current, list):
            current = []

        if rel.childId not in current:
            parent.childrenIds = current + [rel.childId]   # SAFE UPDATE

    # ---------------- UPDATE CHILD ----------------
    result = await db.execute(
        select(Member).where(Member.id == rel.childId)
    )
    child = result.scalars().first()

    if child:
        current = child.parentIds or []

        if not isinstance(current, list):
            current = []

        if rel.parentId not in current:
            child.parentIds = current + [rel.parentId]   # SAFE UPDATE

    await db.commit()
    await db.refresh(new_rel)

    return new_rel