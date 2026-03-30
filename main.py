from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import auth, mariage, members, parentchild, relationships, tree
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

#origins = os.getenv("URL_ORIGINS", "")
#origins = [url.strip() for url in origins.split(",") if url.strip()]

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,     
    allow_credentials=True,
    allow_methods=["*"],        
    allow_headers=["*"],       
)

# Register routers
app.include_router(members.router)
app.include_router(relationships.router)
app.include_router(mariage.router)
app.include_router(parentchild.router)
app.include_router(tree.router)
app.include_router(auth.router)

# Pour servir les images
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return {"message": "Welcome to the family tree API"}



