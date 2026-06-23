import os
from dotenv import load_dotenv
from pymongo import ASCENDING
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

load_dotenv()

MONGODB_URL = os.getenv("MONGO_URI")
if not MONGODB_URL:
    raise Exception("MONGO_URI is missing in environment variables")

DB_NAME = "tree_family"

client = AsyncIOMotorClient(
    MONGODB_URL,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=10000,
)
db = client[DB_NAME]