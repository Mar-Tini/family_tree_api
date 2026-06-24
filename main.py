from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from database import engine, Base

from models_sql import (
    User,
    OTP,
    Member,
    Marriage,
    ParentChild,
    Relationships,
    FamilyTree,
)

from routers import auth, mariage, members, parentchild, relationships, tree

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("Tables vérifiées/créées avec succès")

    except Exception as e:
        print(f"Erreur création tables : {e}")

    yield


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://family-tree-n7zw3jxrs-0-tinis-projects.vercel.app", 
        "https://family-tree-liard-psi.vercel.app",
        "https://vercel.app",
        "https://*.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Routers
app.include_router(members.router)
app.include_router(relationships.router)
app.include_router(mariage.router)
app.include_router(parentchild.router)
app.include_router(tree.router)
app.include_router(auth.router)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return {"message": "Welcome to the family tree API"}