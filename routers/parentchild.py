from fastapi import APIRouter, HTTPException
from typing import List
from models import ParentChild
from database import db  

router = APIRouter(prefix="/parentchild", tags=["parentchild"])

@router.get("/", response_model=List[ParentChild])
def get_parentchild():
    rels = list(db["relationships"].find({"type": "parentChild"}, {"_id": 0}))
    return rels


@router.post("/", response_model=ParentChild)
def add_parentchild(rel: ParentChild):
    # Vérifier si la relation existe déjà
    existing = db["relationships"].find_one({
        "type": "parentChild",
        "parentId": rel.parentId,
        "childId": rel.childId
    })
    if existing:
        raise HTTPException(status_code=400, detail="Relation already exists")

    # Ajouter la relation
    db["relationships"].insert_one({
        "type": "parentChild",
        **rel.dict()
    })

    # Mettre à jour les références dans "members"
    db["members"].update_one(
        {"id": rel.parentId},
        {"$addToSet": {"childrenIds": rel.childId}}
    )
    db["members"].update_one(
        {"id": rel.childId},
        {"$addToSet": {"parentIds": rel.parentId}}
    )

    return rel
