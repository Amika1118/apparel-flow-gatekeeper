import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, Role, Recipe
from app.seed import seed_recipes, seed_users
from app.settings import settings
from app.schemas import OrderCreate
from app.services.order_service import create_order


@pytest.fixture(scope="session")
def engine():
    # Use in-memory SQLite with a static connection to prevent data loss between sessions
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    # Ensure seed data is present for tests
    seed_recipes(session)
    seed_users(session)

    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def get_user_email_for_role(role: Role) -> str:
    mapping = {
        Role.CUTTING_SUPERVISOR: "supervisor@apparelflow.test",
        Role.CUTTING_VERIFIER: "verifier@apparelflow.test",
        Role.SEWING_SUPERVISOR: "sewing@apparelflow.test",
    }
    return mapping.get(role, "supervisor@apparelflow.test")


@pytest.fixture
def auth_headers(client):
    def _auth_headers(role: Role):
        email = get_user_email_for_role(role)
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": settings.DEMO_PASSWORD},
        )
        data = response.json()
        return {"Authorization": f"Bearer {data['access_token']}"}

    return _auth_headers


def get_user(db, role: Role):
    return db.query(User).filter(User.role == role).first()


def make_order(db, recipe_code: str, target_qty: int, status: str, counts: dict = None):
    if counts is None:
        counts = {}

    supervisor = get_user(db, Role.CUTTING_SUPERVISOR)
    recipe = db.query(Recipe).filter(Recipe.code == recipe_code).first()

    payload = OrderCreate(
        recipe_id=recipe.id,
        target_qty=target_qty,
        fabric_roll_id="R-TEST",
        actual_fabric_yds=100.00,
        items=[],
    )
    order = create_order(db, supervisor, payload)

    for item in order.items:
        comp_name = item.component.component_name
        if comp_name in counts:
            item.actual_qty = counts[comp_name]
            # Simple item status evaluation logic if applicable
            item.status = "MATCH" if item.actual_qty == item.expected_qty else "SHORTAGE"

    order.status = status
    db.commit()
    db.refresh(order)
    return order