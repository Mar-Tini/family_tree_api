import uuid
from fastapi import APIRouter, HTTPException, Depends
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models_sql import FamilyTree, Member, Marriage, ParentChild, Relationships

router = APIRouter(prefix="/trees", tags=["trees"])

familyTrees: List[FamilyTree] = []


# ---------------- BUILD TREE ----------------
async def build_tree_from_get_db(user_id: str, db: AsyncSession) -> List[FamilyTree]:

    global familyTrees
    processed_ids = set()

    result = await db.execute(
        select(Member).where(Member.generation == 1)
    )
    roots = result.scalars().all()

    for root in roots:

        if root.id in processed_ids:
            continue

        members = []
        marriages = []
        parentChild = []

        async def collect_member(member_id: str):

            if member_id in processed_ids:
                return

            result = await db.execute(
                select(Member).where(Member.id == member_id)
            )
            m = result.scalars().first()

            if not m:
                return

            members.append(m)
            processed_ids.add(member_id)

            for c_id in (m.childrenIds or []):
                parentChild.append(
                    ParentChild(
                        id=f"{member_id}_{c_id}",
                        parentId=member_id,
                        childId=c_id,
                        userId=user_id
                    )
                )
                await collect_member(c_id)

            if m.spouseId:
                result = await db.execute(
                    select(Member).where(Member.id == m.spouseId)
                )
                spouse = result.scalars().first()

                if spouse:
                    await collect_member(spouse.id)

                    marriages.append(
                        Marriage(
                            id=f"{member_id}_{spouse.id}",
                            spouseIds=[member_id, spouse.id],
                            userId=user_id
                        )
                    )

        await collect_member(root.id)

        if members:

            tree = FamilyTree(
                treeId=root.id,
                name=f"{root.firstName} {root.lastName}",
                ownerId=user_id,
                members=members,
                relationships=Relationships(
                    marriages=marriages,
                    parentChild=parentChild
                ),
                published=False
            )

            familyTrees.append(tree)

            result = await db.execute(
                select(FamilyTree).where(FamilyTree.treeId == tree.treeId)
            )
            exists = result.scalars().first()

            if not exists:
                db.add(tree)
                await db.commit()

    return familyTrees


# ---------------- GET TREES ----------------
@router.get("/", response_model=List[FamilyTree])
async def get_trees(user_id: str = None, db: AsyncSession = Depends(get_db)):

    if user_id:
        result = await db.execute(
            select(FamilyTree).where(FamilyTree.ownerId == user_id)
        )
    else:
        result = await db.execute(
            select(FamilyTree).where(FamilyTree.published == True)
        )

    return result.scalars().all()


# ---------------- GET ALL ----------------
@router.get("/all", response_model=List[FamilyTree])
async def get_all_trees(db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(FamilyTree).where(FamilyTree.published == True)
    )

    return result.scalars().all()


# ---------------- FIND MEMBERS TREE ----------------
@router.get("/find_members/{user_id}", response_model=FamilyTree)
async def get_tree(user_id: str, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(FamilyTree).where(FamilyTree.ownerId == user_id)
    )

    tree = result.scalars().first()

    if not tree:
        raise HTTPException(status_code=404, detail="Aucun arbre trouvé")

    return tree


# ---------------- ADD TREE ----------------
@router.post("/add/{userid}", response_model=List[FamilyTree])
async def get_user_trees(userid: str, db: AsyncSession = Depends(get_db)):

    return await build_tree_from_get_db(userid, db)


# ---------------- CREATE / UPDATE TREE ----------------
async def create_or_update_family_tree(userId: str, db: AsyncSession):

    result = await db.execute(
        select(Member).where(Member.userId == userId)
    )
    members_list = result.scalars().all()

    if not members_list:
        raise HTTPException(status_code=404, detail="No data found")

    marriages = []
    parent_child = []

    for m in members_list:

        for c_id in (m.childrenIds or []):
            parent_child.append(
                ParentChild(
                    id=str(uuid.uuid4()),
                    parentId=m.id,
                    childId=c_id,
                    userId=userId
                )
            )

        if m.spouseId:
            marriages.append(
                Marriage(
                    id=str(uuid.uuid4()),
                    spouseIds=[m.id, m.spouseId],
                    userId=userId
                )
            )

    tree_name = "Family Tree"
    for m in members_list:
        if m.generation == 1 and m.lastName:
            tree_name = m.lastName
            break

    result = await db.execute(
        select(FamilyTree).where(FamilyTree.ownerId == userId)
    )
    existing = result.scalars().first()

    if existing:
        existing.name = tree_name
        existing.members = members_list
        existing.relationships = Relationships(
            marriages=marriages,
            parentChild=parent_child
        )

        await db.commit()
        await db.refresh(existing)
        return existing

    tree = FamilyTree(
        treeId=str(uuid.uuid4()),
        name=tree_name,
        ownerId=userId,
        members=members_list,
        relationships=Relationships(
            marriages=marriages,
            parentChild=parent_child
        ),
        published=False
    )

    db.add(tree)
    await db.commit()
    await db.refresh(tree)

    return tree


# ---------------- FAMILY TREE ENDPOINT ----------------
@router.get("/familytree/{userId}", response_model=FamilyTree)
async def get_tree_family(userId: str, db: AsyncSession = Depends(get_db)):

    return await create_or_update_family_tree(userId, db)