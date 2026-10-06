import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

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

from sqlalchemy.orm import Mapped, validates, relationship
from sqlalchemy.testing.schema import mapped_column

from app.databse import Base
from app.errors import ImmutableRecordError


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


class Recipe(Base):
    __tablename__ = "recipe_compenent"
    __table_args__ = (
        CheckConstraint("std_fabric_yards > 0", name="check_std_fabric_yards_positive"),
        CheckConstraint("wastage_cap >= 0", name="check_wastage_cap_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, auto_incremrnt=True)
    recipie_code : Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name : Mapped[str] = mapped_column(String(255), nullable=False)
    category : Mapped[str] = mapped_column(String(255), nullable=False)
    std_fabric_yards : Mapped[Decimal] = mapped_column(Numeric(6,2), nullable=False)
    wastage_cap : Mapped[Decimal] = mapped_column(Numeric(5,2), nullable=False)

    components : Mapped[List["RecipeComponent"]] = relationship(
        "RecipeComponent", back_populates="recipe", cascade="all, delete-orphan"
    )


class RecipeComponent(Base):
    __table__ = "recipe_components"
    __table_args__ = (
        UniqueConstraint("recipe_id", "component_name", name="uq_recipe_component_name"),
        CheckConstraint("pieces_per_garment >= 1", name="check_pieces_per_garment_gte_one"),
    )

    id : Mapped[int] = mapped_column(primary_key=True, auto_increment=True)
    recipe_id : Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    component_name : Mapped[str] = mapped_column(String(255), nullable=False)
    pieces_per_garment : Mapped[int] = mapped_column(nullable=False)
    image_url : Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="components")


class CuttingOrder(Base):
    __table__ = "cutting_orders"
    __table_args__ = (
        CheckConstraint("target_qty >= 1", name="check_target_qty_gte_one"),
        CheckConstraint("actual_fabric_yds > 0", name="check_actual_fabric_yds_positive"),
    )

    id : Mapped[int] = mapped_column(primary_key=True, auto_increment=True)
    order_no : Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    recipe_id : Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    target_qty : Mapped[int] = mapped_column(nullable=False)
    fabric_roll_id : Mapped[str] = mapped_column(String(255), nullable=False)
    actual_fabric_yds : Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    status : OrderStatus = mapped_column(OrderStatus, nullable=False)
    created_by : Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at : Mapped[datetime] = mapped_column(
                                    DateTime(timezone=True),
                                    default=lambda : datetime.now(datetime.timezone.utc),
                                    nullable=False,
                                    )
    updated_at : Mapped[datetime] = mapped_column(
                                    DateTime(timezone=True),
                                    default=lambda : datetime.now(datetime.timezone.utc),
                                    onupdate=lambda : datetime.now(datetime.timezone.utc),
                                    nullable=False,
                                    )

    recipe: Mapped["Recipe"] = relationship("Recipe")
    creator: Mapped["User"] = relationship("User")
    items: Mapped[List["VerificationItem"]] = relationship(
        "VerificationItem", back_populates="order", cascade="all, delete-orphan"
    )
    logs: Mapped[List["VerificationLog"]] = relationship(
        "VerificationLog", back_populates="order", cascade="all, delete-orphan"
    )


class VerificationItem(Base):
    """Represents a specific verified component item under a cutting order."""

    __tablename__ = "verification_items"
    __table_args__ = (
        UniqueConstraint("order_id", "component_id", name="uq_order_component"),
        CheckConstraint("expected_qty >= 1", name="check_expected_qty_gte_one"),
        CheckConstraint("actual_qty IS NULL OR actual_qty >= 0", name="check_actual_qty_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("cutting_orders.id"), nullable=False)
    component_id: Mapped[int] = mapped_column(ForeignKey("recipe_components.id"), nullable=False)
    expected_qty: Mapped[int] = mapped_column(nullable=False)
    actual_qty: Mapped[Optional[int]] = mapped_column(nullable=True)
    status: Mapped[Optional[TrafficFlag]] = mapped_column(SQLEnum(TrafficFlag), nullable=True)

    order: Mapped["CuttingOrder"] = relationship("CuttingOrder", back_populates="items")
    component: Mapped["RecipeComponent"] = relationship("RecipeComponent")



class VerificationLog(Base):
    __tablename__ = "verification_logs"
    __table_args__ = (
        CheckConstraint(
            "(decision != 'REJECTED') OR (rejection_note IS NOT NULL AND length(trim(rejection_note)) > 0)",
            name="check_rejection_note_required_on_rejection",
        ),
    )

    id : Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id : Mapped[int] = mapped_column(ForeignKey("cutting_orders.id"), nullable=False)
    verifier_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    decision : Mapped[Decision] = mapped_column(nullable=False)
    rejection_note : Mapped[Optional[str]] = mapped_column(Text,nullable=True)
    wastage_pct : Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=False)
    timestamp : Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    order: Mapped["CuttingOrder"] = relationship("CuttingOrder", back_populates="logs")
    verifier: Mapped["User"] = relationship("User")

    @validates("rejection_note")
    def validate_rejection_note(self, key: str, rejection_note: Optional[str]) -> Optional[str]:
        if self.decision == Decision.REJECTED and (not rejection_note or not rejection_note.strip()):
            raise ValueError("Rejection note is required when decision is REJECTED.")
        return rejection_note


@event.listens_for(VerificationLog, "before_update")
def prevent_verification_log_update(mapper, connection, target):
    raise ImmutableRecordError("VerificationLog records are immutable and cannot be updated.")

@event.listens_for(VerificationLog, "before_delete")
def prevent_verification_log_delete(mapper, connection, target):
    raise ImmutableRecordError("VerificationLog records are immutable and cannot be deleted.")