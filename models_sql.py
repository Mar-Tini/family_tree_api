from sqlalchemy import Column, String, Boolean, Integer, DateTime, JSON
from database import Base


class User(Base):
    __tablename__ = "users"

    userId = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)
    status = Column(Boolean, default=False)


class OTP(Base):
    __tablename__ = "otps"

    id = Column(String, primary_key=True)
    email = Column(String, index=True)
    code = Column(String)
    expire_at = Column(DateTime)


class Member(Base):
    __tablename__ = "members"

    id = Column(String, primary_key=True)
    firstName = Column(String)
    lastName = Column(String)
    gender = Column(String)
    generation = Column(Integer)

    birthDate = Column(String, nullable=True)
    deathDate = Column(String, nullable=True)
    photo = Column(String, nullable=True)

    spouseId = Column(String, nullable=True)

    parentIds = Column(JSON, default=list)
    childrenIds = Column(JSON, default=list)

    userId = Column(String, index=True)


class Marriage(Base):
    __tablename__ = "marriages"

    id = Column(String, primary_key=True)
    spouseIds = Column(JSON, default=list)
    marriageDate = Column(String, nullable=True)
    childrenIds = Column(JSON, default=list)
    userId = Column(String, index=True)


class ParentChild(Base):
    __tablename__ = "parentchild"

    id = Column(String, primary_key=True)
    parentId = Column(String, index=True)
    childId = Column(String, index=True)
    userId = Column(String, index=True)


class Relationships(Base):
    __tablename__ = "relationships"

    id = Column(String, primary_key=True)
    userId = Column(String, index=True)

    marriages = Column(JSON, default=list)
    parentChild = Column(JSON, default=list)


class FamilyTree(Base):
    __tablename__ = "familytrees"

    treeId = Column(String, primary_key=True)
    name = Column(String)
    ownerId = Column(String, index=True)

    members = Column(JSON, default=list)

    relationships = Column(JSON, default=dict)

    published = Column(Boolean, default=True)