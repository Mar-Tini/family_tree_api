from fastapi import APIRouter, HTTPException
from typing import List
from models import Marriage
from database import db   # ta connexion Mongo

router = APIRouter(prefix="/marriages", tags=["marriages"])


@router.get("/", response_model=List[Marriage])
def get_marriages():
    marriages = list(db["relationships"].find(
        {"type": "marriage"},   # on filtre seulement les mariages
        {"_id": 0}
    ))
    return marriages


@router.post("/", response_model=Marriage)
def add_marriage(marriage: Marriage):
    # Vérifier si le mariage existe déjà (même set de spouseIds)
    existing = db["relationships"].find_one({
        "type": "marriage",
        "spouseIds": {"$all": marriage.spouseIds, "$size": len(marriage.spouseIds)}
    })
    if existing:
        raise HTTPException(status_code=400, detail="Marriage already exists")

    # Sauvegarder le mariage
    db["relationships"].insert_one({
        "type": "marriage",
        **marriage.dict()
    })

    # Mettre à jour les membres (ajout du spouseId)
    for spouse_id in marriage.spouseIds:
        other_spouse = [s for s in marriage.spouseIds if s != spouse_id][0]
        db["members"].update_one(
            {"id": spouse_id},
            {"$set": {"spouseId": other_spouse}}
        )

    return marriage
