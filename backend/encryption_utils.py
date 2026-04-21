import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY")

def encrypt_data(data: str) -> str:
    if not data or not ENCRYPTION_KEY:
        return data
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    if not encrypted_data or not ENCRYPTION_KEY:
        return encrypted_data
    try:
        f = Fernet(ENCRYPTION_KEY.encode())
        return f.decrypt(encrypted_data.encode()).decode()
    except Exception:
        # If decryption fails (e.g. key changed or data not encrypted), return as is
        return encrypted_data

def mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return key
    return f"{key[:6]}...{key[-4:]}"
