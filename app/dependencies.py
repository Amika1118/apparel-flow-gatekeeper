from typing import Union, List, Callable

from fastapi.params import Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import AuthenticationError, PermissionDenied
from app.models import User, Role
from app.security import decode_access_token


def get_current_user(
    authorization: Union[str, None] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
    ) -> User:
    """Extracts and verifies JWT bearer token from authorization header, returning the authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("missing token")

    token = authorization.split(" ", 1)[1]
    package = decode_access_token(token)

    user_id = package.get("sub")
    if user_id is None:
        raise AuthenticationError("unknown user")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise AuthenticationError("unknown user")

    token_role = package.get("role")
    user_role_str = user.role.value if isinstance(user.role, Role) else str(user.role)

    if user_role_str != token_role:
        raise AuthenticationError("token is out of date")

    return user


def require_role(allowed_roles: List[Role]) -> Callable[..., User]:
    """Dependency factory returning a validator function that restricts endpoint access by user role."""

    def check(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise PermissionDenied("this role cannot do that")
        return user

    return check
