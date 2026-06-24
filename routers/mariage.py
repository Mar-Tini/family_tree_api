from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models_sql import Relationships, Member
from schemas import MarriageSchema

router = APIRouter(prefix="/marriages", tags=["marriages"])


# ---------------- GET ALL MARRIAGES ----------------
@router.get("/", response_model=List[MarriageSchema])
async def get_marriages(db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(Relationships))
    relations = result.scalars().all()

    output = []

    for r in relations:
        if not isinstance(r.marriages, list):
            continue

        for m in r.marriages:
            if not isinstance(m, dict):
                continue

            output.append(
                MarriageSchema(
                    id=m.get("id"),
                    spouseIds=m.get("spouseIds", []),
                    marriageDate=m.get("marriageDate"),
                    childrenIds=m.get("childrenIds", []),
                    userId=r.userId
                )
            )

    return output


# ---------------- ADD MARRIAGE ----------------
@router.post("/", response_model=MarriageSchema)
async def add_marriage(marriage: MarriageSchema, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Relationships).where(Relationships.userId == marriage.userId)
    )

    relation = result.scalars().first()

    # CREATE IF NOT EXISTS
    if not relation:
        relation = Relationships(
            userId=marriage.userId,
            marriages=[]
        )
        db.add(relation)
        await db.commit()
        await db.refresh(relation)

    # SAFE INIT (VERY IMPORTANT)
    if not isinstance(relation.marriages, list):
        relation.marriages = []

    # CHECK DUPLICATE
    for m in relation.marriages:
        if isinstance(m, dict):
            if set(m.get("spouseIds", [])) == set(marriage.spouseIds):
                raise HTTPException(status_code=400, detail="Marriage already exists")

    # CREATE NEW MARRIAGE (DICT ONLY)
    new_marriage = {
        "id": marriage.id,
        "spouseIds": marriage.spouseIds,
        "marriageDate": marriage.marriageDate,
        "childrenIds": marriage.childrenIds,
        "userId": marriage.userId
    }

    relation.marriages.append(new_marriage)

    await db.commit()
    await db.refresh(relation)

    # ---------------- UPDATE MEMBERS ----------------
    for spouse_id in marriage.spouseIds:
        result = await db.execute(
            select(Member).where(Member.id == spouse_id)
        )

        member = result.scalars().first()

        if member:
            other = [s for s in marriage.spouseIds if s != spouse_id]
            member.spouseId = other[0] if other else None

    await db.commit()

    return marriage