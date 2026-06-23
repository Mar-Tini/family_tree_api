import os
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL is missing in environment variables")

# IMPORTANT: support Neon + Render URLs
# Neon sometimes provides "postgresql://" instead of "postgresql+asyncpg://"
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Ensure async driver
if "asyncpg" not in DATABASE_URL:
    raise Exception("DATABASE_URL must use asyncpg driver (postgresql+asyncpg://)")

# Engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # better for production (avoid heavy logs on Render)
    future=True
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base model
Base = declarative_base()

# Dependency
async def get_db():
    async with SessionLocal() as session:
        yield session