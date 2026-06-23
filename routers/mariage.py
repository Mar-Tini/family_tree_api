from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db

from models_sql import Marriage, Relationships, Member

router = APIRouter(prefix="/marriages", tags=["marriages"])


# ---------------- GET ALL MARRIAGES ----------------
@router.get("/", response_model=List[Marriage])
async def get_marriages(db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Relationships).where(Relationships.type == "marriage")
    )

    marriages = result.scalars().all()
    return marriages


# ---------------- ADD MARRIAGE ----------------
@router.post("/", response_model=Marriage)
async def add_marriage(marriage: Marriage, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Relationships).where(Relationships.type == "marriage")
    )

    existing = result.scalars().all()

    for e in existing:
        if set(e.spouseIds or []) == set(marriage.spouseIds or []):
            raise HTTPException(status_code=400, detail="Marriage already exists")

    # Create marriage
    new_marriage = Relationships(
        type="marriage",
        spouseIds=marriage.spouseIds
    )

    db.add(new_marriage)
    await db.commit()
    await db.refresh(new_marriage)

    # ---------------- UPDATE MEMBERS ----------------
    for spouse_id in marriage.spouseIds:

        result = await db.execute(
            select(Member).where(Member.id == spouse_id)
        )

        member = result.scalars().first()

        if member:
            other_spouse = [
                s for s in marriage.spouseIds if s != spouse_id
            ][0]

            member.spouseId = other_spouse

    await db.commit()

    return new_marriage