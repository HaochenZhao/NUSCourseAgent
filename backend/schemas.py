from pydantic import BaseModel, EmailStr, validator
from typing import Optional

class OTPRequest(BaseModel):
    email: str

    @validator("email")
    def validate_nus_email(cls, v):
        if not v.lower().endswith(".nus.edu") and not v.lower().endswith("nus.edu.sg"):
            raise ValueError("Email must be an official NUS email (.nus.edu or nus.edu.sg)")
        return v.lower()

class OTPVerify(BaseModel):
    email: str
    code: str

class UserSettingsSchema(BaseModel):
    use_free_trial: bool
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    openai_base_url: Optional[str] = None

class UserInfo(BaseModel):
    email: str
    name: Optional[str] = None
    settings: Optional[UserSettingsSchema] = None

    class Config:
        from_attributes = True
