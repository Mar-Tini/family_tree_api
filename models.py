from typing import Any, Dict, List, Optional
from pydantic import BaseModel
    
class User(BaseModel): 
    userId: str
    email:  str
    status: bool = False 
    
class OTP(BaseModel):
    id : str
    email : str
    code: str
    expire_at : str
    
class Member(BaseModel):
    id: str
    firstName: str
    lastName: str
    gender: str
    generation: int
    birthDate: Optional[str] = None
    deathDate: Optional[str] = None
    photo: Optional[str] = None
    spouseId: Optional[str] = None 
    parentIds: Optional[List[str]] = None
    childrenIds: Optional[List[str]] = None
    userId : str

class Marriage(BaseModel):
    id: str
    spouseIds: List[str]              
    marriageDate: Optional[str] = None
    childrenIds: Optional[List[str]] = None
    userId : str
    
class ParentChild(BaseModel):
    id: str
    parentId: str
    childId: str
    userId : str

class Relationships(BaseModel):
    marriages: List[Marriage] = []
    parentChild: List[ParentChild] = []
    userId :  Optional[str] = None
    
    
class FamilyTree(BaseModel):
    treeId: str
    name: str
    ownerId: str 
    members: List[Member] = []
    relationships: Relationships = Relationships()
    published: bool = False