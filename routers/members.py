import os
import shutil
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Member

router = APIRouter(prefix="/members", tags=["members"])

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- GET ALL MEMBERS ----------------
@router.get("/", response_model=List[Member])
async def get_all_members(db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(Member))
    members = result.scalars().all()

    return members


# ---------------- GET ONE MEMBER ----------------
@router.get("/{member_id}", response_model=Member)
async def get_member(member_id: str, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Member).where(Member.id == member_id)
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    return member


# ---------------- ADD MEMBER ----------------
@router.post("/", response_model=Member)
async def add_member(new_member: Member, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Member).where(Member.id == new_member.id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Member ID already exists")

    db.add(new_member)
    await db.commit()

    return new_member


# ---------------- UPDATE MEMBER ----------------
class MemberModify(BaseModel):
    firstName: str
    lastName: str
    birthDate: Optional[str] = None
    deathDate: Optional[str] = None


@router.put("/{member_id}", response_model=MemberModify)
async def update_member(member_id: str, updated_member: MemberModify, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Member).where(Member.id == member_id)
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    member.firstName = updated_member.firstName
    member.lastName = updated_member.lastName
    member.birthDate = updated_member.birthDate
    member.deathDate = updated_member.deathDate

    await db.commit()

    return updated_member


# ---------------- DELETE MEMBER ----------------
@router.delete("/{member_id}")
async def delete_member(member_id: str, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Member).where(Member.id == member_id)
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    await db.delete(member)
    await db.commit()

    return {"message": "Member deleted successfully"}


# ---------------- UPLOAD IMAGE ----------------
@router.post("/{member_id}/upload-image")
async def upload_image(member_id: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Member).where(Member.id == member_id)
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    file_path = os.path.join(UPLOAD_DIR, f"{member_id}.jpg")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    member.photo = f"/static/uploads/{member_id}.jpg"

    await db.commit()

    return {
        "message": "Image uploaded",
        "url": member.photo
    }