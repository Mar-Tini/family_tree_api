import uuid
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from typing import List
from models import FamilyTree, Member, Marriage, ParentChild, Relationships
from database import db

router = APIRouter(prefix="/trees", tags=["trees"])

familyTrees: List[FamilyTree] = []


def build_tree_from_db(user_id: str) -> List[FamilyTree]:
    """
     Crée les arbres familiaux depuis la base si ils n'existent pas en mémoire.
     Vérifie que les couples de génération 1 restent dans le même arbre.
    """
    global familyTrees
    processed_ids = set()  # IDs déjà utilisés dans un arbre

    # Sélection de tous les membres de génération 1
    roots = list(db.members.find({"generation": 1}))

    for root in roots:
        if root["id"] in processed_ids:
            continue

        members = []
        marriages = []
        parentChild = []

        def collect_member(member_id):
            if member_id in processed_ids:
                return
            m = db.members.find_one({"id": member_id})
            if not m:
                return

            members.append(Member(**m))
            processed_ids.add(member_id)

            # Enfants
            for c_id in m.get("childrenIds", []):
                parentChild.append(ParentChild(id=f"{member_id}_{c_id}", parentId=member_id, childId=c_id))
                collect_member(c_id)

            # Conjoint
            spouse_id = m.get("spouseId")
            if spouse_id:
                spouse = db.members.find_one({"id": spouse_id})
                if spouse:
                    collect_member(spouse_id)
                    marriages.append(Marriage(id=f"{member_id}_{spouse_id}", spouseIds=[member_id, spouse_id]))

        # Construire l'arbre à partir de cette racine
        collect_member(root["id"])

        if members:  # éviter arbre vide
            tree = FamilyTree(
                treeId=root["id"],
                name=f"{root['firstName']} {root['lastName']}",
                ownerId=user_id,
                members=members,
                relationships=Relationships(marriages=marriages, parentChild=parentChild)
            )
            familyTrees.append(tree)

            # Vérifier si déjà présent dans MongoDB
            if not db.trees.find_one({"treeId": tree.treeId}):
                db.trees.insert_one(tree.dict())

    return familyTrees


from typing import List


@router.get("/", response_model=List[FamilyTree])
def get_trees(user_id: str = None):
    """
    Si user_id vide -> retourne arbres publiés
    Si user_id fourni -> retourne arbres appartenant à cet utilisateur (même non publiés)
    """
    try:
        if not user_id:
            trees_from_db = db.trees.find({"published": True})
        else:
            trees_from_db = db.trees.find({"ownerId": user_id})
        return [FamilyTree(**t) for t in trees_from_db]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all", response_model=List[FamilyTree])
def get_all_trees():
    """
        Retourne tous les arbres stockés dans MongoDB.
        Accessible à tout le monde (lecture seule).
    """
    trees_from_db = db.trees.find({"published": True})
    trees = [FamilyTree(**t) for t in trees_from_db]
    return trees


@router.get("/find_members/{user_id}", response_model=FamilyTree)
def get_tree(user_id: str):
    """
    Récupère l'arbre familial d'un utilisateur.
    Si aucun arbre n'existe, retourne None.
    """
    try:
        tree = db["trees"].find({"ownerId": user_id})
        if not tree:
            raise HTTPException(status_code=404, detail="Aucun arbre trouvé")
        return tree
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add/{userid}", response_model=List[FamilyTree])
def get_user_trees(userid: str):
    """
        Retourne tous les arbres familiaux de l'utilisateur.
        Si aucun arbre n'existe en DB, les construit depuis les membres.
    """
    try:
        trees = build_tree_from_db(user_id=userid)
        return trees
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def create_or_update_family_tree(userId: str):
    # récupérer tous les membres
    members_cursor = db.members.find({"userId": userId})
    members_list = [
        Member(
            id=m.get("id") or str(m["_id"]),
            firstName=m.get("firstName", ""),
            lastName=m.get("lastName", ""),
            gender=m.get("gender", ""),
            generation=m.get("generation", 0),
            birthDate=m.get("birthDate"),
            deathDate=m.get("deathDate"),
            photo=m.get("photo"),
            spouseId=m.get("spouseId"),
            parentIds=m.get("parentIds", []),
            childrenIds=m.get("childrenIds", []),
            userId=m.get("userId")
        )
        for m in members_cursor
    ]

    # récupérer mariages
    marriages_cursor = db.relationships.find({"userId": userId, "type": "marriage"})
    marriages_list = [
        Marriage(
            id=m.get("id") or str(m["_id"]),
            spouseIds=m.get("spouseIds", []),
            marriageDate=m.get("marriageDate"),
            childrenIds=m.get("childrenIds", []),
            userId=m.get("userId")
        )
        for m in marriages_cursor
    ]

    # récupérer parent-child
    pc_cursor = db.relationships.find({"userId": userId, "type": "parentchild"})
    pc_list = [
        ParentChild(
            id=pc.get("id") or str(pc["_id"]),
            parentId=pc.get("parentId", ""),
            childId=pc.get("childId", ""),
            userId=pc.get("userId")
        )
        for pc in pc_cursor
    ]

    if not members_list and not marriages_list and not pc_list:
        raise HTTPException(status_code=404, detail="No data found for this userId")

    # nom = lastName du premier membre avec generation = 1
    tree_name = "Family Tree"
    for member in members_list:
        if member.generation == 1 and member.lastName:
            tree_name = member.lastName
            break

    relationships = Relationships(
        marriages=marriages_list,
        parentChild=pc_list,
        userId=userId
    )

    # Vérifier si arbre existe déjà
    existing = db.trees.find_one({"ownerId": userId})

    if existing:
        # update
        db.trees.update_one(
            {"ownerId": userId},
            {"$set": {
                "name": tree_name,
                "members": [m.dict() for m in members_list],
                "relationships": relationships.dict()
            }}
        )
        # recharger arbre mis à jour
        updated = db.trees.find_one({"ownerId": userId})
        return FamilyTree(**updated)

    else:
        # create
        family_tree = FamilyTree(
            treeId=str(uuid.uuid4()),
            name=tree_name,
            ownerId=userId,
            members=members_list,
            relationships=relationships,
            published=False
        )
        db.trees.insert_one(family_tree.dict())
        return family_tree


@router.get("/familytree/{userId}", response_model=FamilyTree)
def get_tree_famly(userId: str):
    return create_or_update_family_tree(userId=userId)
