from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)


class BaseSchema(BaseModel):
    """Base model enforcing no extra fields across all schemas."""
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Request / Input Schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseSchema):
    email: EmailStr
    password: str = Field(..., min_length=1)

    @field_validator("email", mode="before")
    @classmethod
    def transform_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str


class OrderCreate(BaseSchema):
    recipe_id: StrictInt
    target_qty: StrictInt = Field(..., ge=1, le=100000)
    fabric_roll_id: str
    actual_fabric_yds: Decimal = Field(..., gt=0, decimal_places=2)

    @field_validator("fabric_roll_id", mode="before")
    @classmethod
    def validate_fabric_roll_id(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("invalid roll id")
        value = v.strip()
        if len(value) == 0 or len(value) > 50:
            raise ValueError("invalid roll id")
        return value


class CountEntry(BaseSchema):
    component_id: StrictInt
    actual_qty: StrictInt = Field(..., ge=0)


class CountSubmission(BaseSchema):
    counts: List[CountEntry] = Field(..., min_length=1)

    @field_validator("counts")
    @classmethod
    def validate_unique_components(cls, v: List[CountEntry]) -> List[CountEntry]:
        ids = [entry.component_id for entry in v]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate component")
        return v


class RejectRequest(BaseSchema):
    note: str

    @field_validator("note", mode="before")
    @classmethod
    def validate_note(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("rejection reason required")
        value = v.strip()
        if len(value) == 0:
            raise ValueError("rejection reason required")
        if len(value) > 500:
            raise ValueError("too long")
        return value


# ---------------------------------------------------------------------------
# Output Shapes (API Response Models)
# ---------------------------------------------------------------------------

class ComponentOut(BaseSchema):
    id: int
    component_name: str
    pieces_per_garment: int
    image_url: Optional[str] = None


class RecipeOut(BaseSchema):
    id: int
    recipe_code: str
    name: str
    category: str
    std_fabric_yards: Decimal
    wastage_cap: Decimal
    components: List[ComponentOut]


class ItemOut(BaseSchema):
    component_id: int
    component_name: str
    image_url: Optional[str] = None
    expected_qty: int
    actual_qty: Optional[int] = None
    variance: Optional[int] = None

    @model_validator(mode="after")
    def calculate_variance(self) -> "ItemOut":
        if self.actual_qty is not None:
            self.variance = self.actual_qty - self.expected_qty
        else:
            self.variance = None
        return self


class GateSummary(BaseSchema):
    green: int
    yellow: int
    red: int
    uncounted: int
    can_approve: bool


class VerificationLogOut(BaseSchema):
    decision: str
    verifier_name: str
    timestamp: datetime
    wastage_pct: Decimal
    rejection_note: Optional[str] = None


class OrderOut(BaseSchema):
    id: int
    order_no: str
    status: str
    recipe_code: str
    recipe_name: str
    target_qty: int
    fabric_roll_id: str
    actual_fabric_yds: Decimal
    expected_fabric_yds: Optional[Decimal] = None
    items: List[ItemOut]
    latest_rejection_note: Optional[str] = None


class CountResultOut(BaseSchema):
    items: List[ItemOut]
    summary: GateSummary


class SewingQueueRow(BaseSchema):
    id: int
    order_no: str
    recipe_name: str
    target_qty: int
    verified_by: str
    verified_at: datetime
    wastage_pct: Decimal


class SewingBatchOut(BaseSchema):
    id: int
    order_no: str
    recipe_name: str
    target_qty: int
    items: List[ItemOut]
    log: VerificationLogOut
    wastage_pct: Decimal
    wastage_cap: Decimal
    over_cap: bool = False

    @model_validator(mode="after")
    def calculate_over_cap(self) -> "SewingBatchOut":
        self.over_cap = self.wastage_pct > self.wastage_cap
        return self