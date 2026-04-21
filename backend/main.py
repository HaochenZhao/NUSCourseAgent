import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

import models
import schemas
import auth
from mailer import send_otp_email
from encryption_utils import encrypt_data, decrypt_data, mask_key
from database import engine, get_db
from agent import CourseAgent

load_dotenv()

# Initialize DB tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="NUS Course Agent API")

# Allow dynamic origins from .env
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = CourseAgent()

# ---------------------------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------------------------

@app.post("/auth/send-otp")
def send_otp(req: schemas.OTPRequest, db: Session = Depends(get_db)):
    code = auth.generate_otp()
    expiry = datetime.utcnow() + timedelta(minutes=auth.OTP_EXPIRE_MINUTES)
    
    # Store or update OTP
    db_otp = db.query(models.OTP).filter(models.OTP.email == req.email).first()
    if db_otp:
        db_otp.code = code
        db_otp.expires_at = expiry
    else:
        db_otp = models.OTP(email=req.email, code=code, expires_at=expiry)
        db.add(db_otp)
    
    db.commit()
    
    # Send OTP (Email or Terminal fallback)
    import asyncio
    asyncio.create_task(send_otp_email(req.email, code))
    
    return {"message": "OTP sent"}

@app.post("/auth/verify-otp")
def verify_otp(req: schemas.OTPVerify, db: Session = Depends(get_db)):
    db_otp = db.query(models.OTP).filter(models.OTP.email == req.email).first()
    
    if not db_otp or db_otp.code != req.code or db_otp.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Check if user exists, else create
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user:
        user = models.User(email=req.email)
        db.add(user)
        # Create default settings
        settings = models.UserSettings(user_id=req.email, use_free_trial=True)
        db.add(settings)
        db.commit()
    
    # Delete OTP after successful verify
    db.delete(db_otp)
    db.commit()
    
    access_token = auth.create_access_token(data={"sub": req.email})
    return {"access_token": access_token, "token_type": "bearer"}

# ---------------------------------------------------------------------------
# User Routes
# ---------------------------------------------------------------------------

@app.get("/users/me", response_model=schemas.UserInfo)
def read_user_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.get("/users/me/settings", response_model=schemas.UserSettingsSchema)
def get_settings(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    settings = db.query(models.UserSettings).filter(models.UserSettings.user_id == current_user.email).first()
    if not settings:
        settings = models.UserSettings(user_id=current_user.email, use_free_trial=True)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    # Mask the API key for the UI
    response_settings = schemas.UserSettingsSchema(
        use_free_trial=settings.use_free_trial,
        openai_api_key=mask_key(decrypt_data(settings.openai_api_key)),
        openai_model=settings.openai_model,
        openai_base_url=settings.openai_base_url
    )
    return response_settings

@app.post("/users/me/settings", response_model=schemas.UserSettingsSchema)
def update_settings(
    settings_data: schemas.UserSettingsSchema,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    settings = db.query(models.UserSettings).filter(models.UserSettings.user_id == current_user.email).first()
    if not settings:
        settings = models.UserSettings(user_id=current_user.email)
        db.add(settings)
    
    settings.use_free_trial = settings_data.use_free_trial
    
    # Only update API key if it's not a masked key being sent back
    if settings_data.openai_api_key and "..." not in settings_data.openai_api_key:
        settings.openai_api_key = encrypt_data(settings_data.openai_api_key)
    
    settings.openai_model = settings_data.openai_model
    settings.openai_base_url = settings_data.openai_base_url
    
    db.commit()
    db.refresh(settings)
    
    return schemas.UserSettingsSchema(
        use_free_trial=settings.use_free_trial,
        openai_api_key=mask_key(decrypt_data(settings.openai_api_key)),
        openai_model=settings.openai_model,
        openai_base_url=settings.openai_base_url
    )

# ---------------------------------------------------------------------------
# Chat Route
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    profile: Dict = {}
    history: List[Dict] = []

@app.post("/chat/stream")
async def chat_stream(
    req: ChatRequest, 
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Fetch user settings
    settings = db.query(models.UserSettings).filter(models.UserSettings.user_id == current_user.email).first()
    
    llm_config = None
    if settings and not settings.use_free_trial:
        llm_config = {
            "api_key": decrypt_data(settings.openai_api_key),
            "base_url": settings.openai_base_url,
            "model": settings.openai_model,
        }

    def event_generator():
        for event in agent.stream_chat(req.message, req.profile, req.history, llm_config=llm_config):
            event_type = event.get("event", "unknown")
            data = event.get("data", {})
            yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/")
def root():
    return {"status": "ok", "service": "NUS Course Agent"}

@app.get("/health")
def health():
    return agent.test_connection()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
