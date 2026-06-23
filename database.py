import os
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from motor.motor_asyncio import AsyncIOMotorClient
import certifi


load_dotenv()

# =========================
# CONFIG
# =========================
MONGODB_URL = os.getenv("MONGO_URI")


if not MONGODB_URL:
    raise Exception("MONGO_URL is missing in environment variables")

DB_NAME = "tree_family"
# =========================
# CONNECTION
# =========================

client = AsyncIOMotorClient(
    MONGODB_URL,
    tls=True,
    tlsAllowInvalidCertificates=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=10000,
)

db = client[DB_NAME]

COLLECTIONS = {
    "members": "members",
    "relationships": "relationships",
    "trees": "trees",
    "users": "users",
    "otps": "otps"
}

# =========================
# INIT DATABASE (INDEX ONLY)
# =========================
def init_db():
    """
    Crée les index MongoDB.
    Fonction idempotente (safe à appeler plusieurs fois).
    """

    try:
        # MEMBERS
        db[COLLECTIONS["members"]].create_index("id", unique=True)

        # RELATIONSHIPS
        db[COLLECTIONS["relationships"]].create_index("parentId")
        db[COLLECTIONS["relationships"]].create_index("childId")

        # TREES
        db[COLLECTIONS["trees"]].create_index("treeId", unique=True)

        # USERS
        db[COLLECTIONS["users"]].create_index(
            [("email", ASCENDING)],
            unique=True
        )

        # OTPS
        db[COLLECTIONS["otps"]].create_index("otpId", unique=True)

        print("MongoDB indexes initialized successfully.")

    except Exception as e:
        print(f"Mongo init error: {e}")


# =========================
# FASTAPI DEPENDENCY
# =========================
def get_db():
    return db