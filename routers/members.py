import os
import shutil
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models_sql import Member  

router = APIRouter(prefix="/members", tags=["members"])

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- Pydantic SCHEMAS ----------------

class MemberCreate(BaseModel):
    id: str
    firstName: str
    lastName: str
    gender: str
    generation: int
    birthDate: Optional[str] = None
    deathDate: Optional[str] = None
    photo: Optional[str] = None
    userId: str


class MemberUpdate(BaseModel):
    firstName: str
    lastName: str
    birthDate: Optional[str] = None
    deathDate: Optional[str] = None


class MemberOut(MemberCreate):
    class Config:
        from_attributes = True


# ---------------- GET ALL MEMBERS ----------------
@router.get("/", response_model=List[MemberOut])
async def get_all_members(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Member))
    return result.scalars().all()


# ---------------- GET ONE MEMBER ----------------
@router.get("/{member_id}", response_model=MemberOut)
async def get_member(member_id: str, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Member).where(Member.id == member_id)
    )
    member = result.scalars().first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    return member


# ---------------- ADD MEMBER ----------------
@router.post("/", response_model=MemberOut)
async def add_member(new_member: MemberCreate, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Member).where(Member.id == new_member.id)
    )
    existing = result.scalars().first()

    if existing:
        raise HTTPException(status_code=400, detail="Member ID already exists")

    member = Member(**new_member.dict())  # 

    db.add(member)
    await db.commit()
    await db.refresh(member)

    return member


# ---------------- UPDATE MEMBER ----------------
@router.put("/{member_id}", response_model=MemberOut)
async def update_member(
    member_id: str,
    updated: MemberUpdate,
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(
        select(Member).where(Member.id == member_id)
    )
    member = result.scalars().first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    member.firstName = updated.firstName
    member.lastName = updated.lastName
    member.birthDate = updated.birthDate
    member.deathDate = updated.deathDate

    await db.commit()
    await db.refresh(member)

    return member


# ---------------- DELETE MEMBER ----------------
@router.delete("/{member_id}")
async def delete_member(member_id: str, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Member).where(Member.id == member_id)
    )
    member = result.scalars().first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    await db.delete(member)
    await db.commit()

    return {"message": "Member deleted successfully"}


# ---------------- UPLOAD IMAGE ----------------
@router.post("/{member_id}/upload-image")
async def upload_image(
    member_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(
        select(Member).where(Member.id == member_id)
    )
    member = result.scalars().first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    file_path = os.path.join(UPLOAD_DIR, f"{member_id}.jpg")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    member.photo = f"/static/uploads/{member_id}.jpg"

    await db.commit()
    await db.refresh(member)

    return {
        "message": "Image uploaded",
        "url": member.photo
    }