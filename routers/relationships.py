from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Marriage, ParentChild, Relationships

router = APIRouter(prefix="/Relationships", tags=["Relationships"])

# ---------------- GET MARRIAGES ----------------
@router.get("/marriages", response_model=List[Marriage])
async def get_marriages(db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Relationships).where(Relationships.type == "marriage")
    )

    return result.scalars().all()


# ---------------- GET PARENT-CHILD ----------------
@router.get("/parentchild", response_model=List[ParentChild])
async def get_parent_child(db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Relationships).where(Relationships.type == "parentChild")
    )

    return result.scalars().all()