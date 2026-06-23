import os
import random
import smtplib
import ssl
from uuid import uuid4
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

from database import get_db
from models import FamilyTree, Relationships

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

router = APIRouter(prefix="/auth", tags=["auth"])

SMTPSERVER = os.getenv("SMTP_SERVER")
SMTPPORT = int(os.getenv("SMTP_PORT", 465))
SMTPEMAIL = os.getenv("SMTP_EMAIL")
SMTPPASS = os.getenv("SMTP_PASSWORD")


class EmailRequest(BaseModel):
    email: EmailStr

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    code: str


def send_email(to_email: str, code: str):
    msg = MIMEText(f"Votre code de vérification est : {code}")
    msg["Subject"] = "Code de vérification"
    msg["From"] = SMTPEMAIL
    msg["To"] = to_email

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTPSERVER, SMTPPORT, context=context) as server:
        server.login(SMTPEMAIL, SMTPPASS)
        server.sendmail(SMTPEMAIL, to_email, msg.as_string())


@router.post("/request-code")
async def request_code(data: EmailRequest, db=Depends(get_db)):
    code = f"{random.randint(100000, 999999)}"

    await db["otps"].delete_one({"email": data.email})
    await db["otps"].insert_one({
        "email": data.email,
        "code": code,
        "expire_at": datetime.utcnow() + timedelta(minutes=5)
    })

    try:
        send_email(data.email, code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur envoi email: {e}")

    return {"message": "Code envoyé"}


@router.post("/verify-code")
async def verify_code(data: OTPVerifyRequest, db=Depends(get_db)):
    otp_entry = await db["otps"].find_one({"email": data.email})
    if not otp_entry:
        raise HTTPException(status_code=400, detail="Aucun code trouvé")
    if datetime.utcnow() > otp_entry["expire_at"]:
        raise HTTPException(status_code=400, detail="Code expiré")
    if otp_entry["code"] != data.code:
        raise HTTPException(status_code=400, detail="Code invalide")

    await db["otps"].delete_one({"email": data.email})

    existing_user = await db["users"].find_one({"email": data.email})
    if existing_user:
        user_id = str(existing_user["_id"])
        await db["users"].update_one(
            {"_id": existing_user["_id"]},
            {"$set": {"status": True}}
        )
        user = {"userId": user_id, "email": existing_user["email"], "status": True}
    else:
        result = await db["users"].insert_one({"email": data.email, "status": True})
        user_id = str(result.inserted_id)
        user = {"userId": user_id, "email": data.email, "status": True}

    trees_count = await db["trees"].count_documents({"ownerId": user_id})
    if trees_count == 0:
        new_tree = FamilyTree(
            treeId=str(uuid4()),
            name="Nouvel arbre",
            ownerId=user_id,
            members=[],
            relationships=Relationships()
        )
        await db["trees"].insert_one(new_tree.dict())

    trees_cursor = db["trees"].find({"ownerId": user_id})
    trees = await trees_cursor.to_list(length=None)
    for t in trees:
        t["treeId"] = str(t["_id"])
        t.pop("_id", None)

    return {
        "message": "Utilisateur et arbre vérifiés/créés avec succès",
        "user": user,
        "trees": trees
    }


@router.post("/logout/{userId}")
async def logout(userId: str, db=Depends(get_db)):
    user = await db["users"].find_one({"_id": ObjectId(userId)})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    await db["users"].update_one(
        {"_id": ObjectId(userId)},
        {"$set": {"status": False}}
    )
    return {"message": "Utilisateur déconnecté avec succès"}