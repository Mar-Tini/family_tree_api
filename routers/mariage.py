from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db

from models_sql import Marriage, Relationships, Member
from schemas import MarriageSchema   

router = APIRouter(prefix="/marriages", tags=["marriages"])


# ---------------- GET ALL MARRIAGES ----------------
@router.get("/", response_model=List[MarriageSchema])
async def get_marriages(db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Relationships).where(Relationships.userId.isnot(None))
    )

    data = result.scalars().all()

    # convert DB -> schema format
    return [
        MarriageSchema(
            id=r.id,
            spouseIds=r.marriages[0] if r.marriages else [],
            marriageDate=None,
            childrenIds=[],
            userId=r.userId
        )
        for r in data
    ]


# ---------------- ADD MARRIAGE ----------------
@router.post("/", response_model=MarriageSchema)
async def add_marriage(marriage: MarriageSchema, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Relationships).where(Relationships.userId == marriage.userId)
    )

    existing = result.scalars().all()

    for e in existing:
        if e.marriages and marriage.spouseIds in e.marriages:
            raise HTTPException(status_code=400, detail="Marriage already exists")

    new_relation = Relationships(
        userId=marriage.userId,
        marriages=[marriage.spouseIds]
    )

    db.add(new_relation)
    await db.commit()
    await db.refresh(new_relation)

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

    return MarriageSchema(
        id=new_relation.id,
        spouseIds=marriage.spouseIds,
        marriageDate=None,
        childrenIds=[],
        userId=marriage.userId
    )