from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    CuttingOrder,
    Recipe,
    RecipeComponent,
    User,
    Role,
)
from app.security import hash_password
from app.settings import settings
from app.services.order_service import create_order, submit_for_verification
from app.services.verification_service import record_counts, approve, reject
from app.schemas import OrderCreate, ItemInput, CountSubmission, CountItemInput

RECIPE_DATA = [
    {
        "code": "REC-BL01",
        "name": "Casual Blouse",
        "category": "Blouse",
        "std_fabric_yards": 1.8,
        "wastage_cap": 5.0,
        "components": [
            ("Front Body Panel", 1),
            ("Back Body Panel", 1),
            ("Sleeves (Left & Right)", 2),
            ("Collar & Stand", 1),
            ("Sleeve Cuffs", 2),
        ],
    },
    {
        "code": "REC-CT02",
        "name": "Crop Top",
        "category": "Crop Top",
        "std_fabric_yards": 1.1,
        "wastage_cap": 8.0,
        "components": [
            ("Front Chest Panel", 1),
            ("Back Support Panel", 1),
            ("Neck Binding Strip", 1),
            ("Hem Elastic Casing", 1),
            ("Side Strap Accents", 2),
        ],
    },
]

USER_DATA = [
    {
        "email": "supervisor@apparelflow.test",
        "role": UserRole.CUTTING_SUPERVISOR,
        "full_name": "Demo Cutting Supervisor",
    },
    {
        "email": "verifier@apparelflow.test",
        "role": UserRole.CUTTING_VERIFIER,
        "full_name": "Demo Cutting Verifier",
    },
    {
        "email": "sewing@apparelflow.test",
        "role": UserRole.SEWING_SUPERVISOR,
        "full_name": "Demo Sewing Supervisor",
    },
]


def seed_recipes(db: Session) -> None:
    for recipe_info in RECIPE_DATA:
        existing = db.query(Recipe).filter(Recipe.code == recipe_info["code"]).first()
        if existing:
            continue

        recipe = Recipe(
            code=recipe_info["code"],
            name=recipe_info["name"],
            category=recipe_info["category"],
            std_fabric_yards=recipe_info["std_fabric_yards"],
            wastage_cap=recipe_info["wastage_cap"],
        )
        db.add(recipe)
        db.flush()

        for name, pieces in recipe_info["components"]:
            component = RecipeComponent(
                recipe_id=recipe.id,
                component_name=name,
                pieces_per_unit=pieces,
            )
            db.add(component)
    db.commit()


def seed_users(db: Session) -> None:
    for user_info in USER_DATA:
        existing = db.query(User).filter(User.email == user_info["email"]).first()
        if existing:
            continue

        user = User(
            email=user_info["email"],
            password_hash=hash_password(settings.DEMO_PASSWORD),
            role=user_info["role"],
            full_name=user_info["full_name"],
        )
        db.add(user)
    db.commit()


def seed_demo_orders(db: Session) -> None:
    if db.query(CuttingOrder).first():
        return

    supervisor = db.query(User).filter(User.role == UserRole.CUTTING_SUPERVISOR).first()
    verifier = db.query(User).filter(User.role == UserRole.CUTTING_VERIFIER).first()

    blouse_recipe = db.query(Recipe).filter(Recipe.code == "REC-BL01").first()
    crop_recipe = db.query(Recipe).filter(Recipe.code == "REC-CT02").first()

    if not supervisor or not verifier or not blouse_recipe or not crop_recipe:
        return

    # o1: stays CUTTING_IN_PROGRESS
    create_order(
        db,
        supervisor,
        OrderCreate(
            recipe_id=blouse_recipe.id,
            target_qty=50,
            fabric_roll_id="R-101",
            actual_fabric_yds=92.0,
            items=[ItemInput(component_id=c.id, actual_qty=c.pieces_per_unit * 50) for c in blouse_recipe.components],
        ),
    )

    # o2: PENDING_VERIFICATION
    o2_order = create_order(
        db,
        supervisor,
        OrderCreate(
            recipe_id=crop_recipe.id,
            target_qty=40,
            fabric_roll_id="R-102",
            actual_fabric_yds=45.0,
            items=[ItemInput(component_id=c.id, actual_qty=c.pieces_per_unit * 40) for c in crop_recipe.components],
        ),
    )
    submit_for_verification(db, o2_order.id, supervisor)

    # o3: REJECTED
    o3_order = create_order(
        db,
        supervisor,
        OrderCreate(
            recipe_id=blouse_recipe.id,
            target_qty=20,
            fabric_roll_id="R-103",
            actual_fabric_yds=38.0,
            items=[ItemInput(component_id=c.id, actual_qty=c.pieces_per_unit * 20) for c in blouse_recipe.components],
        ),
    )
    submit_for_verification(db, o3_order.id, supervisor)

    # Record counts with a shortage on first component and reject
    o3_items = db.query(CuttingOrder).filter(CuttingOrder.id == o3_order.id).first().items
    record_counts(
        db,
        o3_order.id,
        CountSubmission(items=[CountItemInput(item_id=o3_items[0].id, actual_qty=o3_items[0].expected_qty - 5)]),
    )
    reject(db, o3_order.id, verifier, "Significant piece shortage detected on front panel cutting.")

    # o4: VERIFIED
    o4_order = create_order(
        db,
        supervisor,
        OrderCreate(
            recipe_id=crop_recipe.id,
            target_qty=30,
            fabric_roll_id="R-104",
            actual_fabric_yds=34.0,
            items=[ItemInput(component_id=c.id, actual_qty=c.pieces_per_unit * 30) for c in crop_recipe.components],
        ),
    )
    submit_for_verification(db, o4_order.id, supervisor)

    o4_items = db.query(CuttingOrder).filter(CuttingOrder.id == o4_order.id).first().items
    record_counts(
        db,
        o4_order.id,
        CountSubmission(items=[CountItemInput(item_id=i.id, actual_qty=i.expected_qty) for i in o4_items]),
    )
    approve(db, o4_order.id, verifier)


def run() -> None:
    db = SessionLocal()
    try:
        seed_recipes(db)
        seed_users(db)
        seed_demo_orders(db)
    finally:
        db.close()


if __name__ == "__main__":
    run()