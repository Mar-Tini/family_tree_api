import os
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from typing import List, Optional
from pydantic import BaseModel
from models import Member
from database import get_db

router = APIRouter(prefix="/members", tags=["members"])

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/", response_model=List[Member])
async def get_all_members(db=Depends(get_db)):
    members = await db.members.find({}, {"_id": 0}).to_list(length=None)
    return members


@router.get("/{member_id}", response_model=Member)
async def get_member(member_id: str, db=Depends(get_db)):
    member = await db.members.find_one({"id": member_id}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.post("/", response_model=Member)
async def add_member(new_member: Member, db=Depends(get_db)):
    existing = await db.members.find_one({"id": new_member.id})
    if existing:
        raise HTTPException(status_code=400, detail="Member ID already exists")
    await db.members.insert_one(new_member.dict())
    return new_member


class MemberModify(BaseModel):
    firstName: str
    lastName: str
    birthDate: Optional[str] = None
    deathDate: Optional[str] = None


@router.put("/{member_id}", response_model=MemberModify)
async def update_member(member_id: str, updated_member: MemberModify, db=Depends(get_db)):
    result = await db.members.update_one(
        {"id": member_id},
        {"$set": updated_member.dict()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    return updated_member


@router.delete("/{member_id}")
async def delete_member(member_id: str, db=Depends(get_db)):
    result = await db.members.delete_one({"id": member_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"message": "Member deleted successfully"}


@router.post("/{member_id}/upload-image")
async def upload_image(member_id: str, file: UploadFile = File(...), db=Depends(get_db)):
    member = await db.members.find_one({"id": member_id})
    if not member:
        raise HTTPException(404, "Member not found")

    file_path = os.path.join(UPLOAD_DIR, f"{member_id}.jpg")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    await db.members.update_one(
        {"id": member_id},
        {"$set": {"photo": f"/static/uploads/{member_id}.jpg"}}
    )
    return {"message": "Image uploaded", "url": f"/static/uploads/{member_id}.jpg"}