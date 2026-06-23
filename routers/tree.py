import uuid
from fastapi import APIRouter, HTTPException
from typing import List

from models import FamilyTree, Member, Marriage, ParentChild, Relationships
from database import get_db  

router = APIRouter(prefix="/trees", tags=["trees"])

familyTrees: List[FamilyTree] = []


# ---------------- BUILD TREE ----------------
async def build_tree_from_get_db(user_id: str) -> List[FamilyTree]:

    global familyTrees
    processed_ids = set()

    roots = await get_db.members.find({"generation": 1}).to_list(length=None)

    for root in roots:
        if root["id"] in processed_ids:
            continue

        members = []
        marriages = []
        parentChild = []

        async def collect_member(member_id):

            if member_id in processed_ids:
                return

            m = await get_db.members.find_one({"id": member_id})
            if not m:
                return

            members.append(Member(**m))
            processed_ids.add(member_id)

            # children
            for c_id in m.get("childrenIds", []):
                parentChild.append(
                    ParentChild(
                        id=f"{member_id}_{c_id}",
                        parentId=member_id,
                        childId=c_id
                    )
                )
                await collect_member(c_id)

            # spouse
            spouse_id = m.get("spouseId")
            if spouse_id:
                spouse = await get_db.members.find_one({"id": spouse_id})
                if spouse:
                    await collect_member(spouse_id)
                    marriages.append(
                        Marriage(
                            id=f"{member_id}_{spouse_id}",
                            spouseIds=[member_id, spouse_id]
                        )
                    )

        await collect_member(root["id"])

        if members:
            tree = FamilyTree(
                treeId=root["id"],
                name=f"{root['firstName']} {root['lastName']}",
                ownerId=user_id,
                members=members,
                relationships=Relationships(
                    marriages=marriages,
                    parentChild=parentChild
                )
            )

            familyTrees.append(tree)

            exists = await get_db.trees.find_one({"treeId": tree.treeId})
            if not exists:
                await get_db.trees.insert_one(tree.dict())

    return familyTrees


# ---------------- GET TREES ----------------
@router.get("/", response_model=List[FamilyTree])
async def get_trees(user_id: str = None):

    if not user_id:
        trees = await get_db.trees.find({"published": True}).to_list(length=None)
    else:
        trees = await get_db.trees.find({"ownerId": user_id}).to_list(length=None)

    return [FamilyTree(**t) for t in trees]


# ---------------- GET ALL ----------------
@router.get("/all", response_model=List[FamilyTree])
async def get_all_trees():

    trees = await get_db.trees.find({"published": True}).to_list(length=None)

    return [FamilyTree(**t) for t in trees]


# ---------------- FIND MEMBERS TREE ----------------
@router.get("/find_members/{user_id}", response_model=FamilyTree)
async def get_tree(user_id: str):

    tree = await get_db.trees.find_one({"ownerId": user_id})

    if not tree:
        raise HTTPException(status_code=404, detail="Aucun arbre trouvé")

    return tree


# ---------------- ADD TREE ----------------
@router.post("/add/{userid}", response_model=List[FamilyTree])
async def get_user_trees(userid: str):

    trees = await build_tree_from_get_db(user_id=userid)
    return trees


# ---------------- CREATE / UPDATE TREE ----------------
async def create_or_update_family_tree(userId: str):

    members_cursor = get_db.members.find({"userId": userId})
    members_list = []

    async for m in members_cursor:
        members_list.append(
            Member(
                id=m.get("id"),
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
        )

    marriages_cursor = get_db.relationships.find(
        {"userId": userId, "type": "marriage"}
    )
    marriages_list = [m async for m in marriages_cursor]

    pc_cursor = get_db.relationships.find(
        {"userId": userId, "type": "parentchild"}
    )
    pc_list = [p async for p in pc_cursor]

    if not members_list and not marriages_list and not pc_list:
        raise HTTPException(status_code=404, detail="No data found")

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

    existing = await get_db.trees.find_one({"ownerId": userId})

    if existing:
        await get_db.trees.update_one(
            {"ownerId": userId},
            {"$set": {
                "name": tree_name,
                "members": [m.dict() for m in members_list],
                "relationships": relationships.dict()
            }}
        )
        return await get_db.trees.find_one({"ownerId": userId})

    family_tree = FamilyTree(
        treeId=str(uuid.uuid4()),
        name=tree_name,
        ownerId=userId,
        members=members_list,
        relationships=relationships,
        published=False
    )

    await get_db.trees.insert_one(family_tree.dict())
    return family_tree


@router.get("/familytree/{userId}", response_model=FamilyTree)
async def get_tree_family(userId: str):
    return await create_or_update_family_tree(userId)