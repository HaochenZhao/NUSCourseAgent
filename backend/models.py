from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    email = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=True)
    
    settings = relationship("UserSettings", back_populates="user", uselist=False)

class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.email"))
    
    use_free_trial = Column(Boolean, default=True)
    openai_api_key = Column(String, nullable=True)
    openai_model = Column(String, nullable=True)
    openai_base_url = Column(String, nullable=True)

    user = relationship("User", back_populates="settings")

class OTP(Base):
    __tablename__ = "otps"

    email = Column(String, primary_key=True, index=True)
    code = Column(String)
    expires_at = Column(DateTime)
