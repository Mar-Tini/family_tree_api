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

    result = await db.execute(
        select(Relationships)
    )

    relations = result.scalars().all()

    marriages_out = []

    for r in relations:
        if not r.marriages:
            continue

        for m in r.marriages:
            marriages_out.append(
                MarriageSchema(
                    id=m.get("id"),
                    spouseIds=m.get("spouseIds", []),
                    marriageDate=m.get("marriageDate"),
                    childrenIds=m.get("childrenIds", []),
                    userId=r.userId
                )
            )

    return marriages_out


# ---------------- ADD MARRIAGE ----------------
@router.post("/", response_model=MarriageSchema)
async def add_marriage(marriage: MarriageSchema, db: AsyncSession = Depends(get_db)):

    # get or create relationship row
    result = await db.execute(
        select(Relationships).where(Relationships.userId == marriage.userId)
    )
    relation = result.scalars().first()

    if not relation:
        relation = Relationships(
            userId=marriage.userId,
            marriages=[]
        )
        db.add(relation)
        await db.commit()
        await db.refresh(relation)

    # ensure marriages list exists
    if relation.marriages is None:
        relation.marriages = []

    # check duplicate
    for m in relation.marriages:
        if set(m.get("spouseIds", [])) == set(marriage.spouseIds):
            raise HTTPException(status_code=400, detail="Marriage already exists")

    # add new marriage
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