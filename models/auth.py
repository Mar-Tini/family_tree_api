from pydantic import BaseModel


class EmailRequest(BaseModel):
    email: str

class OTPVerifyRequest(BaseModel):
    email: str
    code: str
