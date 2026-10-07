from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Union

import jwt
from passlib.context import CryptContext

from app.config import Settings
from app.errors import AuthenticationError


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain_text: str) -> str:
    return pwd_context.hash(plain_text)

def verify_password(plain_password: str, stored_hash: str) -> bool:
    return pwd_context.verify(plain_password, stored_hash)

def create_access_token(user_id: Union[int, str], role: str) -> str:
    now = datetime.datetime.utcnow()
    role_str = role.value if hasattr(role, "value") else role

    payload = {
        "sub" : str(user_id),
        "role" : role_str,
        "iat" : now,
        "exp" : now + timedelta(minutes=Settings.TOKEN_EXPIRATION_MINUTES)
    }

    return jwt.encode(
        payload,
        Settings.JWT_SECRET_KEY,
        algorithm= Settings.JWT_ALGORITHM
    )

def decode_access_token(token: str) -> Dict[str, Any] :
    try:
        payload = jwt.decode(
            token,
            Settings.JWT_SECRET_KEY,
            algorithms=[Settings.JWT_ALGORITHM]
        )
        return payload
    except Exception as err:
        raise AuthenticationError("invalid or expired token") from err