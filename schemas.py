# shemas.py
from pydantic import BaseModel, Field
from typing import List, Optional


# ---------------- USER ----------------
class UserSchema(BaseModel):
    userId: str
    email: str
    status: bool = False

    class Config:
        from_attributes = True


# ---------------- OTP ----------------
class OTPSchema(BaseModel):
    id: str
    email: str
    code: str
    expire_at: str

    class Config:
        from_attributes = True


# ---------------- MEMBER ----------------


class MemberSchema(BaseModel):
    id: str
    firstName: str
    lastName: str
    gender: str
    generation: int

    birthDate: Optional[str] = None
    deathDate: Optional[str] = None
    photo: Optional[str] = None

    spouseId: Optional[str] = None

    parentIds: List[str] = Field(default_factory=list)
    childrenIds: List[str] = Field(default_factory=list)

    userId: str

    class Config:
        from_attributes = True
        
# ---------------- MARRIAGE ----------------

class MarriageSchema(BaseModel):
    id: str
    spouseIds: List[str] = Field(default_factory=list)
    marriageDate: Optional[str] = None
    childrenIds: List[str] = Field(default_factory=list)
    userId: Optional[str] = None

    class Config:
        from_attributes = True
# ---------------- RELATIONSHIPS ----------------
class RelationshipsSchema(BaseModel):
    id: Optional[str] = None
    userId: Optional[str] = None
    marriages: List[MarriageSchema] = []
    parentChild: List[dict] = []

    class Config:
        from_attributes = True


# ---------------- FAMILY TREE ----------------
class FamilyTreeSchema(BaseModel):
    treeId: str
    name: str
    ownerId: str

    members: List[MemberSchema] = []
    relationships: RelationshipsSchema

    published: bool = False

    class Config:
        from_attributes = True