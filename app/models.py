import datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
)

from sqlalchemy.orm import Mapped, validates
from sqlalchemy.testing.schema import mapped_column

from app.databse import Base


class Role(str, Enum):
    CUTTING_SUPERVISOR = "cutting_supervisor"
    CUTTING_VERIFIER = "cutting_verifier"
    SEWING_SUPERVISOR = "sewing_supervisor"

class OrderStatus(str, Enum):
    CUTTING_IN_PROGRESS = "cutting_in_progress"
    PENDING_VERIFICATION = "pending_verification"
    COUNT_QC = "count_qc"
    REJECTED = "rejected"
    VERIFIED = "verified"
    IN_SEWING = "in_sewing"

class TrafficFlag(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

class Decision(str, Enum):
    YES = "yes"
    NO = "no"

class User(Base):
    __tablename__ = "users"
    id : Mapped[int] = mapped_column(primary_key=True, auto_increment=True)
    email : Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash : Mapped[str] = mapped_column(String(255), nullable=False)
    role : Mapped[Role] = mapped_column(SQLEnum(Role), nullable=False)
    full_name : Mapped[str] = mapped_column(String(255), nullable=False)
    created_at : Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    @validates("email")
    def validate_email(self, key:str, email:str):
        if not email:
            raise ValueError("Email cannot be empty")
        return email.strip().lower()


class
