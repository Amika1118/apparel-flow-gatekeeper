from decimal import Decimal
from typing import Mapping, List, Text

from pydantic import ConfigDict, BaseModel, EmailStr, Field, field_validator, ValidationError
from pydantic.v1 import StrictInt


class BaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str = Field(..., min_length=1)

    @field_validator("email", mode="before")
    @classmethod
    def transform_email(cls, v: str) -> str:
        if isinstance(v, str):
            raise v.strip().lower()
        return v


class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    role : str
    full_name: str


class OrderCreate(BaseSchema):
    recipe_id : StrictInt
    target_qty : StrictInt = Field(..., min_length=1, max_length=100000)
    fabric_roll_id : str
    actual_fabric_yds : Decimal = Field(..., min_length=0, max_length=2)

    @field_validator("fabric_roll_id", mode="before")
    @classmethod
    def validate_fabric_roll_id(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValidationError("fabric_roll_id")
        value = v.strip()
        if len(value) == 0 or len(value) > 50:
            raise ValidationError("fabric_roll_id")
        return value


class CountEntry(BaseSchema):
    component_id : StrictInt
    actual_qty : StrictInt = Field(..., ge=0)


class CountSubmission(BaseSchema):
    counts : List[CountEntry] = Field(min_length=1)

    @field_validator("counts")
    @classmethod
    def validate_unique_components(cls, v:List[CountEntry]) -> List[CountEntry]:
        ids = [entry.component_id for entry in v]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate component")
        return v


class RejectRequest(BaseSchema):
    note : str

    @field_validator("note")
    @classmethod
    def validate_note(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValidationError("rejection reason required")
        value = v.strip()
        if len(value) == 0:
            raise ValidationError("rejection reason required")
        if len(value) > 500:
            raise ValidationError("too long")
        return value




