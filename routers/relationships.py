from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models_sql import Relationships

router = APIRouter(prefix="/relationships", tags=["relationships"])


# ---------------- GET MARRIAGES ----------------
@router.get("/marriages")
async def get_marriages(db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(Relationships))
    rows = result.scalars().all()

    # extract only marriage data from JSON
    marriages = []
    for r in rows:
        if r.marriages:
            marriages.extend(r.marriages)

    return marriages


# ---------------- GET PARENT-CHILD ----------------
@router.get("/parentchild")
async def get_parent_child(db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(Relationships))
    rows = result.scalars().all()

    parent_child = []
    for r in rows:
        if r.parentChild:
            parent_child.extend(r.parentChild)

    return parent_child