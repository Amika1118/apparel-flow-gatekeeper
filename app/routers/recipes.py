from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.errors import NotFoundError
from app.models import Recipe, Role
from app.schemas import RecipeOut

router = APIRouter(prefix="/recipes", tags=["Recipes"])


@router.get("", response_model=List[RecipeOut])
def list_recipes(
    db: Session = Depends(get_db),
    _: any = Depends(require_role(Role.CUTTING_SUPERVISOR)),
) -> List[RecipeOut]:
    """Retrieves a list of all cutting recipes for authorized cutting supervisors."""
    recipes = db.query(Recipe).all()
    return recipes


@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    _: any = Depends(require_role(Role.CUTTING_SUPERVISOR)),
) -> RecipeOut:
    """Retrieves a specific cutting recipe by ID for authorized cutting supervisors."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise NotFoundError("recipe not found")
    return recipe