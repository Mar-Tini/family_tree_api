import os
import random
import smtplib
import ssl
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models_sql import OTP, User, FamilyTree

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------- ENV ----------------
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


# ---------------- CHECK SMTP ----------------
# def check_smtp_config():
  #  if not SMTP_SERVER or not SMTP_EMAIL or not SMTP_PASSWORD:
       # raise HTTPException(status_code=500, detail="SMTP not configured")


# ---------------- REQUEST MODELS ----------------
class EmailRequest(BaseModel):
    email: str


class OTPVerifyRequest(BaseModel):
    email: str
    code: str


# ---------------- EMAIL ----------------
def send_email(to_email: str, code: str):

    # check_smtp_config()

    msg = MIMEText(f"Votre code de vérification est : {code}")
    msg["Subject"] = "Code de vérification"
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email error: {str(e)}")


# ---------------- REQUEST CODE ----------------
@router.post("/request-code")
async def request_code(data: EmailRequest, db: AsyncSession = Depends(get_db)):

    try:
        code = str(random.randint(100000, 999999))

        # delete old OTP
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

        # IMPORTANT: email after DB success
        send_email(data.email, code)

        return {"message": "Code envoyé"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            relationships={},   # safe JSON
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