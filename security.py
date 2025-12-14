from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],   # 👈 IMPORTANT
    deprecated="auto"
)
