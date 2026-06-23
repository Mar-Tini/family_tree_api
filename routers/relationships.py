from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Marriage, ParentChild, Relationship

router = APIRouter(prefix="/relationships", tags=["relationships"])

# ---------------- GET MARRIAGES ----------------
@router.get("/marriages", response_model=List[Marriage])
async def get_marriages(db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Relationship).where(Relationship.type == "marriage")
    )

    return result.scalars().all()


# ---------------- GET PARENT-CHILD ----------------
@router.get("/parentchild", response_model=List[ParentChild])
async def get_parent_child(db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Relationship).where(Relationship.type == "parentChild")
    )

    return result.scalars().all()