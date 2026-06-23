# app/main.py
import os
from uuid import uuid4
from bson import ObjectId
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
import random, smtplib, ssl
from email.mime.text import MIMEText
from datetime import datetime, timedelta

from pytest import Session
from database import db, get_db  
from models import OTP, FamilyTree, Member, Relationships, User
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
import os
from pathlib import Path


env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class EmailRequest(BaseModel):
    email: EmailStr

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    code: str

router = APIRouter(prefix="/auth", tags=["auth"])

SMTPSERVER = os.getenv("SMTP_SERVER")
SMTPPORT = int(os.getenv("SMTP_PORT", 465))
SMTPEMAIL = os.getenv("SMTP_EMAIL")
SMTPPASS = os.getenv("SMTP_PASSWORD")

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
def request_code(data: EmailRequest):
    code = f"{random.randint(100000, 999999)}"

    # supprimer l'ancien OTP s'il existe
    db["otp"].delete_one({"email": data.email})

    # stocker OTP en DB
    db["otp"].insert_one({
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
def verify_code(data: OTPVerifyRequest):
    # Vérifier OTP
    otp_entry = db["otp"].find_one({"email": data.email})
    if not otp_entry:
        raise HTTPException(status_code=400, detail="Aucun code trouvé")
    if datetime.utcnow() > otp_entry["expire_at"]:
        raise HTTPException(status_code=400, detail="Code expiré")
    if otp_entry["code"] != data.code:
        raise HTTPException(status_code=400, detail="Code invalide")

    # supprimer OTP après usage
    db["otp"].delete_one({"email": data.email})

    # Vérifier si l'utilisateur existe
    existing_user = db["users"].find_one({"email": data.email})
    if existing_user:
        user_id = str(existing_user["_id"])
        # mettre à jour le status à True
        db["users"].update_one({"_id": existing_user["_id"]}, {"$set": {"status": True}})
        user = {"userId": user_id, "email": existing_user["email"], "status": True}
    else:
        # créer utilisateur
        result = db["users"].insert_one({"email": data.email, "status": True})
        user_id = str(result.inserted_id)
        user = {"userId": user_id, "email": data.email, "status": True}

    # Créer un nouvel arbre
    # Vérifier si aucun arbre pour cet utilisateur
    trees_count = db.trees.count_documents({"ownerId": user_id})
    if trees_count == 0:
        new_tree = FamilyTree(
            treeId=str(uuid4()),
            name="Nouvel arbre",
            ownerId=user_id,
            members=[],
            relationships=Relationships()
        )
        db.trees.insert_one(new_tree.dict())

    # Récupérer tous les arbres pour l'utilisateur
    trees = list(db.trees.find({"ownerId": user_id}))
    for t in trees:
        t["treeId"] = str(t["_id"])  # convertir ObjectId en str
        t.pop("_id", None)

    return {
        "message": "Utilisateur et arbre vérifiés/créés avec succès",
        "user": user,
        "trees": trees
    }
    
    
    
@router.post("/logout/{userId}")
def logout(userId : str):
 
    user = db.users.find_one({"_id": ObjectId(userId)})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    # Mettre status à False
    db.users.update_one({"_id": ObjectId(userId)}, {"$set": {"status": False}})
    return {"message": "Utilisateur déconnecté avec succès"}