from fastapi import APIRouter
from typing import List
from models import Marriage, ParentChild
from database import db

router = APIRouter(prefix="/relationships", tags=["relationships"])

@router.get("/marriages", response_model=List[Marriage])
def get_marriages():
    marriages = list(db["relationships"].find({"type": "marriage"}, {"_id": 0}))
    return marriages

@router.get("/parentchild", response_model=List[ParentChild])
def get_parent_child():
    parent_child = list(db["relationships"].find({"type": "parentChild"}, {"_id": 0}))
    return parent_child
