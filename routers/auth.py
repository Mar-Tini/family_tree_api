import os
import random
import smtplib
import ssl
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from uuid import uuid4
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv

from database import get_db
from models_sql import OTP, User, FamilyTree, Relationships

# Load env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------- ENV SMTP ----------------
SMTPSERVER = os.getenv("SMTP_SERVER")
SMTPPORT = int(os.getenv("SMTP_PORT", 465))
SMTPEMAIL = os.getenv("SMTP_EMAIL")
SMTPPASS = os.getenv("SMTP_PASSWORD")

# ---------------- REQUEST MODELS ----------------
class EmailRequest(BaseModel):
    email: str

class OTPVerifyRequest(BaseModel):
    email: str
    code: str


# ---------------- EMAIL ----------------
def send_email(to_email: str, code: str):
    msg = MIMEText(f"Votre code de vérification est : {code}")
    msg["Subject"] = "Code de vérification"
    msg["From"] = SMTPEMAIL
    msg["To"] = to_email

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTPSERVER, SMTPPORT, context=context) as server:
        server.login(SMTPEMAIL, SMTPPASS)
        server.sendmail(SMTPEMAIL, to_email, msg.as_string())


# ---------------- REQUEST CODE ----------------
@router.post("/request-code")
async def request_code(data: EmailRequest, db: AsyncSession = Depends(get_db)):

    code = str(random.randint(100000, 999999))

    result = await db.execute(select(OTP).where(OTP.email == data.email))
    old_otp = result.scalars().first()

    if old_otp:
        await db.delete(old_otp)
        await db.commit()

    otp = OTP(
        id=str(uuid4()),
        email=data.email,
        code=code,
        expire_at=datetime.utcnow() + timedelta(minutes=5)
    )

    db.add(otp)
    await db.commit()

    send_email(data.email, code)

    return {"message": "Code envoyé"}


# ---------------- VERIFY CODE ----------------
@router.post("/verify-code")
async def verify_code(data: OTPVerifyRequest, db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(OTP).where(OTP.email == data.email))
    otp = result.scalars().first()

    if not otp:
        raise HTTPException(400, "Aucun code trouvé")

    if datetime.utcnow() > otp.expire_at:
        raise HTTPException(400, "Code expiré")

    if otp.code != data.code:
        raise HTTPException(400, "Code invalide")

    await db.delete(otp)
    await db.commit()

    # ---------------- USER ----------------
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()

    if user:
        user.status = True
    else:
        user = User(
            userId=str(uuid4()),
            email=data.email,
            status=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # ---------------- FAMILY TREE ----------------
    result = await db.execute(
        select(FamilyTree).where(FamilyTree.ownerId == user.userId)
    )
    tree = result.scalars().first()

    if not tree:
        tree = FamilyTree(
            treeId=str(uuid4()),
            name="Nouvel arbre",
            ownerId=user.userId,
            members=[],
            relationships=Relationships(),
            published=False
        )
        db.add(tree)
        await db.commit()

    return {
        "message": "OK",
        "user": {
            "email": user.email,
            "status": user.status,
            "userId": user.userId
        }
    }


# ---------------- LOGOUT ----------------
@router.post("/logout/{userId}")
async def logout(userId: str, db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(User).where(User.userId == userId))
    user = result.scalars().first()

    if not user:
        raise HTTPException(404, "Utilisateur non trouvé")

    user.status = False
    await db.commit()

    return {"message": "Utilisateur déconnecté avec succès"}