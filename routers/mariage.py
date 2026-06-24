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

        marriages = r.marriages or []

        if not isinstance(marriages, list):
            marriages = []

        for m in marriages:
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

    # find relation
    result = await db.execute(
        select(Relationships).where(Relationships.userId == marriage.userId)
    )
    relation = result.scalars().first()

    # create if not exists
    if not relation:
        relation = Relationships(
            userId=marriage.userId,
            marriages=[],
            parentChild=[]
        )
        db.add(relation)
        await db.commit()
        await db.refresh(relation)

    # safe init
    existing = relation.marriages or []

    if not isinstance(existing, list):
        existing = []

    # duplicate check
    for m in existing:
        if isinstance(m, dict):
            if set(m.get("spouseIds", [])) == set(marriage.spouseIds):
                raise HTTPException(status_code=400, detail="Marriage already exists")

    # new marriage
    new_marriage = {
        "id": marriage.id,
        "spouseIds": marriage.spouseIds,
        "marriageDate": marriage.marriageDate,
        "childrenIds": marriage.childrenIds,
        "userId": marriage.userId
    }

    # SAFE UPDATE (no append mutation)
    relation.marriages = existing + [new_marriage]

    await db.commit()
    await db.refresh(relation)

    # ---------------- UPDATE MEMBERS ----------------
    for spouse_id in marriage.spouseIds:

        result = await db.execute(
            select(Member).where(Member.id == spouse_id)
        )
        member = result.scalars().first()

        if member:
            others = [s for s in marriage.spouseIds if s != spouse_id]
            member.spouseId = others[0] if others else None

    await db.commit()

    return marriage