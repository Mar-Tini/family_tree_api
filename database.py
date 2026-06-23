import os
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL is missing in environment variables")

DB_NAME = "tree_family"

# Engine (Neon PostgreSQL)
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base for models
Base = declarative_base()


# Dependency (replacement of get_db)
async def get_db():
    async with SessionLocal() as session:
        yield session